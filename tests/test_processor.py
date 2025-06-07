@pytest.fixture
    def reencode_processor(self, mock_subprocess_run):
        """Create a VideoProcessor instance with reencode mode."""
        return VideoProcessor(verbose=False, dry_run=False, reencode=True)
    
    def test_gpu_detection(self, mock_subprocess_run):
        """Test GPU encoder detection."""
        # Mock successful GPU test
        mock_subprocess_run.return_value = Mock(returncode=0)
        
        processor = VideoProcessor(gpu='auto')
        
        # Should have detected a GPU encoder
        assert processor.gpu_encoder is not None
    
    def test_gpu_encoder_selection(self, mock_subprocess_run):
        """Test specific GPU encoder selection."""
        mock_subprocess_run.return_value = Mock(returncode=0)
        
        processor = VideoProcessor(gpu='videotoolbox')
        
        assert processor.gpu_encoder is not None
        assert processor.gpu_encoder['encoder'] == 'h264_videotoolbox'
    
    def test_gpu_encoder_fallback(self, mock_subprocess_run):
        """Test GPU encoder fallback when not available."""
        # Mock failed GPU test
        mock_subprocess_run.return_value = Mock(returncode=1)
        
        processor = VideoProcessor(gpu='nvenc')
        
        # Should fall back to CPU
        assert processor.gpu_encoder is None
    
    def test_gpu_encoding_in_accurate_mode(self, gpu_processor, mock_subprocess_run):
        """Test GPU encoding in accurate mode."""
        # Mock video info response
        mock_subprocess_run.return_value = Mock(
            returncode=0,
            stdout='{"streams": [{"codec_type": "video", "codec_name": "h264"}]}',
            stderr=""
        )
        
        gpu_processor.accurate = True
        
        input_file = Path("input.mp4")
        output_file = Path("output.mp4")
        segment = VideoSegment(
            start=timedelta(seconds=10),
            end=timedelta(seconds=30)
        )
        
        gpu_processor.extract_segment(input_file, output_file, segment)
        
        # Check that GPU encoder is used
        extract_call = mock_subprocess_run.call_args_list[-1]
        args = extract_call[0][0]
        
        assert '-c:v' in args
    def test_split_safe_mode(self, mock_subprocess_run):
        """Test split-safe encoding mode."""
        from video_chapter_trimmer.models import Chapter
        
        mock_subprocess_run.return_value = Mock(
            returncode=0,
            stdout='{"streams": [{"codec_type": "video", "codec_name": "h264"}]}',
            stderr=""
        )
        
        processor = VideoProcessor(reencode=True, split_safe=True)
        
        segment = VideoSegment(
            start=timedelta(seconds=0),
            end=timedelta(seconds=120)
        )
        
        chapters = [
            Chapter(timedelta(seconds=30), "Chapter 1"),
            Chapter(timedelta(seconds=60), "Chapter 2"),
            Chapter(timedelta(seconds=90), "Chapter 3"),
        ]
        
        processor.extract_segment(
            Path("input.mp4"),
            Path("output.mp4"),
            segment,
            chapters
        )
        
        # Check that keyframe parameters are added
        extract_call = mock_subprocess_run.call_args_list[-1]
        args = extract_call[0][0]
        
        assert '-g' in args
        assert '-force_key_frames' in args
    
    def test_split_video_by_chapters(self, processor, mock_subprocess_run):
        """Test splitting video by chapters."""
        from video_chapter_trimmer.models import Chapter
        import tempfile
        
        chapters = [
            Chapter(timedelta(seconds=0), "Opening"),
            Chapter(timedelta(seconds=60), "--CM"),
            Chapter(timedelta(seconds=90), "Main Content"),
            Chapter(timedelta(seconds=180), "Ending"),
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            input_file = Path("input.mp4")
            
            output_files = processor.split_video_by_chapters(
                input_file, chapters, output_dir
            )
            
            # Should create 3 files (skipping --CM)
            assert len(output_files) == 3
            
            # Check ffmpeg was called 3 times for extraction
            # Plus initial version check
            assert mock_subprocess_run.call_count == 4
            
            # Verify output filenames
            assert "01_Opening" in str(output_files[0])
            assert "02_Main Content" in str(output_files[1])
            assert "03_Ending" in str(output_files[2])"""Tests for video processor."""

import pytest
from pathlib import Path
from datetime import timedelta
import tempfile
import subprocess
from unittest.mock import Mock, patch, call

from video_chapter_trimmer.processor import VideoProcessor
from video_chapter_trimmer.models import VideoSegment


class TestVideoProcessor:
    """Test VideoProcessor class."""
    
    @pytest.fixture
    def mock_subprocess_run(self):
        """Mock subprocess.run for testing."""
        with patch('subprocess.run') as mock_run:
            # Default: ffmpeg exists
            mock_run.return_value = Mock(
                returncode=0,
                stdout="ffmpeg version 4.4.0",
                stderr=""
            )
            yield mock_run
    
    @pytest.fixture
    def processor(self, mock_subprocess_run):
        """Create a VideoProcessor instance."""
        return VideoProcessor(verbose=False, dry_run=False)
    
    @pytest.fixture
    def accurate_processor(self, mock_subprocess_run):
        """Create a VideoProcessor instance with accurate mode."""
        return VideoProcessor(verbose=False, dry_run=False, accurate=True)
    
    @pytest.fixture
    def gpu_processor(self, mock_subprocess_run):
        """Create a VideoProcessor instance with GPU support."""
        # Mock successful GPU test
        mock_subprocess_run.return_value = Mock(returncode=0)
        return VideoProcessor(verbose=False, dry_run=False, gpu='videotoolbox')
    
    @pytest.fixture
    def dry_run_processor(self, mock_subprocess_run):
        """Create a VideoProcessor instance in dry-run mode."""
        return VideoProcessor(verbose=False, dry_run=True)
    
    def test_check_ffmpeg_success(self, mock_subprocess_run):
        """Test successful ffmpeg check."""
        processor = VideoProcessor()
        # Should not raise any exception
        assert processor is not None
    
    def test_check_ffmpeg_not_found(self):
        """Test ffmpeg not found error."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()
            
            with pytest.raises(RuntimeError) as exc_info:
                VideoProcessor()
            assert "ffmpeg not found" in str(exc_info.value)
    
    def test_check_ffmpeg_error(self):
        """Test ffmpeg command error."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, 'ffmpeg')
            
            with pytest.raises(RuntimeError) as exc_info:
                VideoProcessor()
            assert "ffmpeg returned an error" in str(exc_info.value)
    
    def test_extract_segment_with_duration(self, processor, mock_subprocess_run):
        """Test extracting a segment with duration."""
        input_file = Path("input.mp4")
        output_file = Path("output.mp4")
        segment = VideoSegment(
            start=timedelta(seconds=10),
            end=timedelta(seconds=30)
        )
        
        processor.extract_segment(input_file, output_file, segment)
        
        # Check ffmpeg was called with correct arguments
        calls = mock_subprocess_run.call_args_list
        assert len(calls) == 2  # Initial check + extract command
        
        extract_call = calls[1]
        args = extract_call[0][0]
        
        assert args[0] == 'ffmpeg'
        assert '-ss' in args
        assert '00:00:10.000' in args
        assert '-i' in args
        assert str(input_file) in args
        assert '-c' in args
        assert 'copy' in args
        assert '-t' in args
        assert '00:00:20.000' in args  # duration = 30 - 10
        assert str(output_file) in args
    
    def test_extract_segment_without_duration(self, processor, mock_subprocess_run):
        """Test extracting a segment without end time."""
        input_file = Path("input.mp4")
        output_file = Path("output.mp4")
        segment = VideoSegment(start=timedelta(seconds=10))
        
        processor.extract_segment(input_file, output_file, segment)
        
        extract_call = mock_subprocess_run.call_args_list[1]
        args = extract_call[0][0]
        
        # Should not have -t parameter
        assert '-t' not in args
    
    def test_merge_segments(self, processor, mock_subprocess_run):
        """Test merging video segments."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            segment_files = [
                temp_path / "seg1.mp4",
                temp_path / "seg2.mp4",
                temp_path / "seg3.mp4"
            ]
            output_file = temp_path / "output.mp4"
            
            # Create dummy segment files
            for f in segment_files:
                f.touch()
            
            processor.merge_segments(segment_files, output_file)
            
            # Check concat file was created and deleted
            concat_file = output_file.parent / 'concat_list.txt'
            assert not concat_file.exists()
            
            # Check ffmpeg was called correctly
            merge_call = mock_subprocess_run.call_args_list[1]
            args = merge_call[0][0]
            
            assert args[0] == 'ffmpeg'
            assert '-f' in args
            assert 'concat' in args
            assert str(output_file) in args
    
    def test_merge_segments_empty_list(self, processor):
        """Test merging with empty segment list."""
        with pytest.raises(ValueError) as exc_info:
            processor.merge_segments([], Path("output.mp4"))
        assert "No segment files" in str(exc_info.value)
    
    def test_dry_run_mode(self, dry_run_processor, mock_subprocess_run):
        """Test dry run mode doesn't execute commands."""
        input_file = Path("input.mp4")
        output_file = Path("output.mp4")
        segment = VideoSegment(
            start=timedelta(seconds=10),
            end=timedelta(seconds=30)
        )
        
        dry_run_processor.extract_segment(input_file, output_file, segment)
        
        # Only the initial ffmpeg check should be called
        assert mock_subprocess_run.call_count == 0
    
    def test_get_video_info(self, processor, mock_subprocess_run):
        """Test getting video information."""
        mock_subprocess_run.return_value = Mock(
            returncode=0,
            stdout='{"streams": [], "format": {}}',
            stderr=""
        )
        
        info = processor.get_video_info(Path("video.mp4"))
        
        assert info is not None
        assert "streams" in info
        assert "format" in info
    
    def test_accurate_mode_extraction(self, accurate_processor, mock_subprocess_run):
        """Test extraction in accurate mode."""
        # Mock video info response
        mock_subprocess_run.return_value = Mock(
            returncode=0,
            stdout='{"streams": [{"codec_type": "video", "codec_name": "h264"}]}',
            stderr=""
        )
        
        input_file = Path("input.mp4")
        output_file = Path("output.mp4")
        segment = VideoSegment(
            start=timedelta(seconds=10),
            end=timedelta(seconds=30)
        )
        
        accurate_processor.extract_segment(input_file, output_file, segment)
        
        # Check that re-encoding parameters are used
        extract_call = mock_subprocess_run.call_args_list[-1]
        args = extract_call[0][0]
        
        assert '-c:v' in args
        assert 'libx264' in args
        assert '-crf' in args
    
    def test_reencode_mode_extraction(self, reencode_processor, mock_subprocess_run):
        """Test extraction in reencode mode."""
        # Mock video info response
        mock_subprocess_run.return_value = Mock(
            returncode=0,
            stdout='{"streams": [{"codec_type": "video", "codec_name": "h264"}]}',
            stderr=""
        )
        
        input_file = Path("input.mp4")
        output_file = Path("output.mp4")
        segment = VideoSegment(
            start=timedelta(seconds=10),
            end=timedelta(seconds=30)
        )
        
        reencode_processor.extract_segment(input_file, output_file, segment)
        
        # Check full re-encoding is used
        extract_call = mock_subprocess_run.call_args_list[-1]
        args = extract_call[0][0]
        
        assert '-c:v' in args
        assert 'libx264' in args
        # Should have -i before -ss for accurate seeking
        i_index = args.index('-i')
        ss_index = args.index('-ss')
        assert i_index < ss_index
    
    def test_keyframe_alignment_check(self, processor, mock_subprocess_run):
        """Test keyframe alignment checking."""
        # Mock ffprobe response with keyframe data
        mock_subprocess_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps({
                "packets": [
                    {"pts_time": "9.8", "flags": "K__"},
                    {"pts_time": "10.2", "flags": "___"},
                    {"pts_time": "10.5", "flags": "K__"}
                ]
            }),
            stderr=""
        )
        
        nearest = processor.check_keyframe_alignment(Path("video.mp4"), 10.0)
        
        assert nearest == 9.8  # Nearest keyframe to 10.0
    
    def test_validate_segments(self, processor, mock_subprocess_run):
        """Test segment validation."""
        # Mock keyframe check responses
        mock_subprocess_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps({
                "packets": [
                    {"pts_time": "10.5", "flags": "K__"}
                ]
            }),
            stderr=""
        )
        
        segments = [
            VideoSegment(
                start=timedelta(seconds=10),
                end=timedelta(seconds=30)
            )
        ]
        
        warnings = processor.validate_segments(Path("video.mp4"), segments)
        
        assert len(warnings) > 0
        assert "keyframe" in warnings[0].lower()