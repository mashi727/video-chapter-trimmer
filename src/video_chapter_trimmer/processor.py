"""Video processing functionality using ffmpeg."""

import json
import logging
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

from .models import VideoSegment
from .utils import TimeParser

logger = logging.getLogger(__name__)


class VideoProcessor:
    """Handles video processing operations using ffmpeg."""
    
    def __init__(self, verbose: bool = False, dry_run: bool = False, 
                 accurate: bool = False, reencode: bool = False,
                 gpu: str = None):
        """
        Initialize VideoProcessor.
        
        Args:
            verbose: Show detailed ffmpeg output
            dry_run: Show commands without executing
            accurate: Use accurate seeking (may require re-encoding)
            reencode: Force re-encoding for precise cuts
            gpu: GPU acceleration type ('auto', 'videotoolbox', 'nvenc', 'qsv', 'amf')
        """
        self.verbose = verbose
        self.dry_run = dry_run
        self.accurate = accurate
        self.reencode = reencode
        self.gpu = gpu
        self._check_ffmpeg()
        
        # Detect and configure GPU encoder
        self.gpu_encoder = None
        if gpu:
            self._configure_gpu_encoder()
    
    def _check_ffmpeg(self):
        """Check if ffmpeg is available."""
        if self.dry_run:
            return
            
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'], 
                capture_output=True, 
                check=True,
                text=True
            )
            # Log ffmpeg version if verbose
            if self.verbose:
                first_line = result.stdout.split('\n')[0]
                logger.debug(f"Using {first_line}")
        except subprocess.CalledProcessError:
            raise RuntimeError(
                "ffmpeg returned an error. Please check your installation."
            )
        except FileNotFoundError:
            raise RuntimeError(
                "ffmpeg not found. Please install ffmpeg and ensure it's in your PATH.\n"
                "Installation instructions: https://ffmpeg.org/download.html"
            )
    
    def _configure_gpu_encoder(self):
        """Configure GPU encoder based on platform and availability."""
        if self.gpu == 'auto':
            # Auto-detect available GPU encoder
            self.gpu_encoder = self._detect_gpu_encoder()
            if self.gpu_encoder:
                logger.info(f"Auto-detected GPU encoder: {self.gpu_encoder['name']}")
            else:
                logger.warning("No GPU encoder detected, falling back to CPU encoding")
        else:
            # Use specified GPU encoder
            encoder_configs = {
                'videotoolbox': {
                    'name': 'VideoToolbox (macOS)',
                    'encoder': 'h264_videotoolbox',
                    'params': ['-profile:v', 'high', '-level', '4.2']
                },
                'nvenc': {
                    'name': 'NVIDIA NVENC',
                    'encoder': 'h264_nvenc',
                    'params': ['-preset', 'p4', '-tune', 'hq', '-profile:v', 'high']
                },
                'qsv': {
                    'name': 'Intel Quick Sync',
                    'encoder': 'h264_qsv',
                    'params': ['-preset', 'medium', '-profile:v', 'high']
                },
                'amf': {
                    'name': 'AMD AMF',
                    'encoder': 'h264_amf',
                    'params': ['-quality', 'balanced', '-profile:v', 'high']
                }
            }
            
            if self.gpu in encoder_configs:
                encoder_config = encoder_configs[self.gpu]
                if self._test_encoder(encoder_config['encoder']):
                    self.gpu_encoder = encoder_config
                    logger.info(f"Using GPU encoder: {encoder_config['name']}")
                else:
                    logger.warning(f"{encoder_config['name']} not available, falling back to CPU encoding")
            else:
                logger.warning(f"Unknown GPU encoder: {self.gpu}")
    
    def _detect_gpu_encoder(self) -> Optional[Dict[str, Any]]:
        """Auto-detect available GPU encoder."""
        import platform
        
        # Platform-specific detection order
        if platform.system() == 'Darwin':  # macOS
            # Try VideoToolbox first on macOS
            encoders = [
                {
                    'name': 'VideoToolbox (macOS)',
                    'encoder': 'h264_videotoolbox',
                    'params': ['-profile:v', 'high', '-level', '4.2']
                }
            ]
        elif platform.system() == 'Windows':
            # Try NVIDIA, then AMD, then Intel on Windows
            encoders = [
                {
                    'name': 'NVIDIA NVENC',
                    'encoder': 'h264_nvenc',
                    'params': ['-preset', 'p4', '-tune', 'hq', '-profile:v', 'high']
                },
                {
                    'name': 'AMD AMF',
                    'encoder': 'h264_amf',
                    'params': ['-quality', 'balanced', '-profile:v', 'high']
                },
                {
                    'name': 'Intel Quick Sync',
                    'encoder': 'h264_qsv',
                    'params': ['-preset', 'medium', '-profile:v', 'high']
                }
            ]
        else:  # Linux
            # Try NVIDIA, then Intel on Linux
            encoders = [
                {
                    'name': 'NVIDIA NVENC',
                    'encoder': 'h264_nvenc',
                    'params': ['-preset', 'p4', '-tune', 'hq', '-profile:v', 'high']
                },
                {
                    'name': 'Intel Quick Sync',
                    'encoder': 'h264_qsv',
                    'params': ['-preset', 'medium', '-profile:v', 'high']
                }
            ]
        
        # Test each encoder
        for encoder in encoders:
            if self._test_encoder(encoder['encoder']):
                return encoder
        
        return None
    
    def _test_encoder(self, encoder: str) -> bool:
        """Test if a specific encoder is available."""
        if self.dry_run:
            return True
            
        try:
            cmd = [
                'ffmpeg',
                '-f', 'lavfi',
                '-i', 'color=c=black:s=320x240:d=1',
                '-c:v', encoder,
                '-f', 'null',
                '-'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            return result.returncode == 0
        except Exception:
            return False
    
    def extract_segment(self, 
                       input_file: Path, 
                       output_file: Path, 
                       segment: VideoSegment) -> None:
        """
        Extract a segment from video file.
        
        Args:
            input_file: Input video file path
            output_file: Output segment file path
            segment: VideoSegment to extract
            
        Raises:
            subprocess.CalledProcessError: If ffmpeg fails
        """
        start_time = TimeParser.format_for_ffmpeg(segment.start)
        
        if self.accurate or self.reencode:
            # Accurate seeking with re-encoding if necessary
            cmd = self._build_accurate_extract_command(
                input_file, output_file, segment, start_time
            )
        else:
            # Fast seeking with stream copy
            cmd = self._build_fast_extract_command(
                input_file, output_file, segment, start_time
            )
        
        self._run_command(cmd, f"Extracting segment to {output_file.name}")
    
    def _build_fast_extract_command(self, input_file: Path, output_file: Path, 
                                   segment: VideoSegment, start_time: str) -> List[str]:
        """Build command for fast extraction using stream copy."""
        cmd = [
            'ffmpeg',
            '-ss', start_time,  # Seek before input (fast seek)
            '-i', str(input_file),
            '-c', 'copy',  # Stream copy for speed
            '-avoid_negative_ts', 'make_zero',
            '-movflags', '+faststart',  # iOS compatibility
        ]
        
        if segment.duration:
            cmd.extend(['-t', TimeParser.format_for_ffmpeg(segment.duration)])
        
        cmd.extend([str(output_file), '-y'])  # Overwrite output
        
        if not self.verbose:
            cmd.extend(['-loglevel', 'error'])
        
        return cmd
    
    def _build_accurate_extract_command(self, input_file: Path, output_file: Path,
                                       segment: VideoSegment, start_time: str) -> List[str]:
        """Build command for accurate extraction with optional re-encoding."""
        # Get video info to determine encoding parameters
        video_info = self.get_video_info(input_file)
        encoding_params = self._get_encoding_params(video_info)
        
        cmd = ['ffmpeg']
        
        if self.reencode:
            # Full re-encoding for most accurate cuts
            cmd.extend([
                '-i', str(input_file),
                '-ss', start_time,  # Seek after input (accurate)
            ])
            cmd.extend(encoding_params)
        else:
            # Accurate seeking with minimal re-encoding
            # Use input seeking for speed, then accurate trimming
            seek_before = max(0, segment.start.total_seconds() - 10)
            cmd.extend([
                '-ss', str(seek_before),  # Rough seek before input
                '-i', str(input_file),
                '-ss', str(segment.start.total_seconds() - seek_before),  # Accurate seek after input
            ])
            
            # Use GPU encoder if available
            if self.gpu_encoder:
                cmd.extend(['-c:v', self.gpu_encoder['encoder']])
                cmd.extend(self.gpu_encoder['params'])
            else:
                cmd.extend([
                    '-c:v', 'libx264',  # Re-encode video for accuracy
                    '-crf', '18',  # High quality
                    '-preset', 'fast',
                ])
            
            cmd.extend(['-c:a', 'copy'])  # Keep audio as-is if possible
        
        if segment.duration:
            cmd.extend(['-t', TimeParser.format_for_ffmpeg(segment.duration)])
        
        cmd.extend([
            '-movflags', '+faststart',
            str(output_file),
            '-y'
        ])
        
        if not self.verbose:
            cmd.extend(['-loglevel', 'error'])
        
        return cmd
    
    def _get_encoding_params(self, video_info: Optional[Dict[str, Any]]) -> List[str]:
        """
        Determine encoding parameters based on source video.
        
        Args:
            video_info: Video information from ffprobe
            
        Returns:
            List of ffmpeg encoding parameters
        """
        params = []
        
        # If GPU encoder is available, use it
        if self.gpu_encoder:
            params.extend(['-c:v', self.gpu_encoder['encoder']])
            params.extend(self.gpu_encoder['params'])
            
            # Add bitrate control for GPU encoders
            if video_info:
                video_stream = next(
                    (s for s in video_info.get('streams', []) 
                     if s['codec_type'] == 'video'), 
                    None
                )
                if video_stream and 'bit_rate' in video_stream:
                    source_bitrate = int(video_stream['bit_rate'])
                    # Use similar bitrate as source
                    target_bitrate = min(source_bitrate, 20_000_000)  # Cap at 20 Mbps
                    params.extend(['-b:v', str(target_bitrate)])
                else:
                    params.extend(['-b:v', '5M'])  # Default 5 Mbps
        else:
            # CPU encoding parameters
            if not video_info:
                # Default high-quality encoding
                return [
                    '-c:v', 'libx264',
                    '-crf', '18',
                    '-preset', 'medium',
                    '-c:a', 'aac',
                    '-b:a', '192k'
                ]
            
            # Analyze source video
            video_stream = None
            for stream in video_info.get('streams', []):
                if stream['codec_type'] == 'video' and not video_stream:
                    video_stream = stream
            
            # Video encoding parameters
            if video_stream:
                params.extend(['-c:v', 'libx264'])
                
                # Quality based on source bitrate
                if 'bit_rate' in video_stream:
                    source_bitrate = int(video_stream['bit_rate'])
                    if source_bitrate > 10_000_000:  # >10 Mbps
                        params.extend(['-crf', '17'])
                    elif source_bitrate > 5_000_000:  # >5 Mbps
                        params.extend(['-crf', '18'])
                    else:
                        params.extend(['-crf', '20'])
                else:
                    params.extend(['-crf', '18'])  # Default high quality
                
                params.extend(['-preset', 'medium'])
                
                # Preserve framerate
                if 'r_frame_rate' in video_stream:
                    params.extend(['-r', video_stream['r_frame_rate']])
        
        # Audio encoding parameters (same for GPU and CPU)
        audio_stream = None
        if video_info:
            for stream in video_info.get('streams', []):
                if stream['codec_type'] == 'audio' and not audio_stream:
                    audio_stream = stream
        
        if audio_stream:
            # Try to copy audio if it's already AAC
            if audio_stream.get('codec_name') == 'aac':
                params.extend(['-c:a', 'copy'])
            else:
                params.extend(['-c:a', 'aac'])
                
                # Match source audio bitrate
                if 'bit_rate' in audio_stream:
                    audio_bitrate = min(int(audio_stream['bit_rate']), 320_000)
                    params.extend(['-b:a', f'{audio_bitrate // 1000}k'])
                else:
                    params.extend(['-b:a', '192k'])
        else:
            params.extend(['-c:a', 'aac', '-b:a', '192k'])
        
        return params
    
    def merge_segments(self, 
                      segment_files: List[Path], 
                      output_file: Path,
                      cleanup_concat: bool = True) -> None:
        """
        Merge multiple video segments into one file.
        
        Args:
            segment_files: List of segment file paths
            output_file: Output video file path
            cleanup_concat: Remove concat list file after merge
            
        Raises:
            subprocess.CalledProcessError: If ffmpeg fails
            ValueError: If no segment files provided
        """
        if not segment_files:
            raise ValueError("No segment files provided for merging")
        
        # Create concat file
        concat_content = '\n'.join(f"file '{f.absolute()}'" for f in segment_files)
        concat_file = output_file.parent / 'concat_list.txt'
        
        try:
            with open(concat_file, 'w', encoding='utf-8') as f:
                f.write(concat_content)
            
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-c', 'copy',
                '-movflags', '+faststart',
                str(output_file),
                '-y'
            ]
            
            if not self.verbose:
                cmd.extend(['-loglevel', 'error'])
            
            self._run_command(cmd, f"Merging {len(segment_files)} segments")
            
        finally:
            if cleanup_concat and concat_file.exists():
                concat_file.unlink()
    
    def get_video_info(self, video_file: Path) -> Optional[Dict[str, Any]]:
        """
        Get basic video information using ffprobe.
        
        Args:
            video_file: Path to video file
            
        Returns:
            Dictionary with video information or None if ffprobe fails
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-print_format', 'json',
                '-show_streams',
                '-show_format',
                str(video_file)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            return json.loads(result.stdout)
            
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
            return None
    
    def check_keyframe_alignment(self, video_file: Path, 
                                timestamp: float) -> Optional[float]:
        """
        Check if timestamp aligns with a keyframe.
        
        Args:
            video_file: Path to video file
            timestamp: Timestamp in seconds
            
        Returns:
            Nearest keyframe timestamp or None if check fails
        """
        try:
            # Get keyframes near the timestamp
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'packet=pts_time,flags',
                '-of', 'json',
                '-read_intervals', f'{max(0, timestamp-5)}%{timestamp+5}',
                str(video_file)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            data = json.loads(result.stdout)
            keyframes = []
            
            for packet in data.get('packets', []):
                if 'K' in packet.get('flags', ''):  # Keyframe
                    pts_time = float(packet.get('pts_time', 0))
                    keyframes.append(pts_time)
            
            if not keyframes:
                return None
            
            # Find nearest keyframe
            nearest = min(keyframes, key=lambda x: abs(x - timestamp))
            return nearest
            
        except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError):
            return None
    
    def validate_segments(self, input_file: Path, 
                         segments: List[VideoSegment]) -> List[str]:
        """
        Validate segments and check for potential issues.
        
        Args:
            input_file: Input video file
            segments: List of segments to validate
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        for i, segment in enumerate(segments):
            # Check keyframe alignment for start time
            start_seconds = segment.start.total_seconds()
            nearest_keyframe = self.check_keyframe_alignment(input_file, start_seconds)
            
            if nearest_keyframe is not None:
                diff = abs(nearest_keyframe - start_seconds)
                if diff > 0.1:  # More than 100ms difference
                    warnings.append(
                        f"Segment {i+1}: Start time {segment.start} is {diff:.3f}s "
                        f"from nearest keyframe. Consider using --accurate or --reencode "
                        f"for precise cutting."
                    )
            
            # Check end time if present
            if segment.end:
                end_seconds = segment.end.total_seconds()
                nearest_keyframe = self.check_keyframe_alignment(input_file, end_seconds)
                
                if nearest_keyframe is not None:
                    diff = abs(nearest_keyframe - end_seconds)
                    if diff > 0.1:
                        warnings.append(
                            f"Segment {i+1}: End time {segment.end} is {diff:.3f}s "
                            f"from nearest keyframe."
                        )
        
        return warnings
    
    def _run_command(self, cmd: List[str], description: str = "") -> None:
        """
        Run a command, respecting dry_run mode.
        
        Args:
            cmd: Command and arguments
            description: Description of what the command does
            
        Raises:
            subprocess.CalledProcessError: If command fails
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] {description}")
            logger.info(f"[DRY RUN] Command: {' '.join(cmd)}")
        else:
            if description and self.verbose:
                logger.debug(f"{description}")
                logger.debug(f"Command: {' '.join(cmd)}")
            
            subprocess.run(cmd, check=True)