"""Tests for video processor."""

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
        assert '-i' in args
        assert str(input_file) in args
        assert '-ss' in args
        assert '00:00:10.000' in args
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
    
    def test_get_video_info_error(self, processor, mock_subprocess_run):
        """Test getting video info with error."""
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, 'ffprobe')
        
        info = processor.get_video_info(Path("video.mp4"))
        
        assert info is None