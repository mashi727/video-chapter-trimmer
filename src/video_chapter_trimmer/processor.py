"""Video processing functionality using ffmpeg."""

import logging
import subprocess
from pathlib import Path
from typing import List, Optional

from .models import VideoSegment
from .utils import TimeParser

logger = logging.getLogger(__name__)


class VideoProcessor:
    """Handles video processing operations using ffmpeg."""
    
    def __init__(self, verbose: bool = False, dry_run: bool = False):
        """
        Initialize VideoProcessor.
        
        Args:
            verbose: Show detailed ffmpeg output
            dry_run: Show commands without executing
        """
        self.verbose = verbose
        self.dry_run = dry_run
        self._check_ffmpeg()
    
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
        cmd = [
            'ffmpeg',
            '-i', str(input_file),
            '-ss', TimeParser.format_for_ffmpeg(segment.start),
            '-c', 'copy',  # Stream copy for speed
            '-avoid_negative_ts', 'make_zero',
            '-movflags', '+faststart',  # iOS compatibility
        ]
        
        if segment.duration:
            cmd.extend(['-t', TimeParser.format_for_ffmpeg(segment.duration)])
        
        cmd.extend([str(output_file), '-y'])  # Overwrite output
        
        if not self.verbose:
            cmd.extend(['-loglevel', 'error'])
        
        self._run_command(cmd, f"Extracting segment to {output_file.name}")
    
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
    
    def get_video_info(self, video_file: Path) -> Optional[dict]:
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
            
            import json
            return json.loads(result.stdout)
            
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
            return None
    
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
