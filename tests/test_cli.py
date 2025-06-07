"""Tests for command-line interface."""

import pytest
from pathlib import Path
import tempfile
import argparse
from unittest.mock import Mock, patch, MagicMock
import sys

from video_chapter_trimmer.cli import (
    VideoChapterTrimmer, 
    create_parser, 
    setup_logging, 
    main
)


class TestCLI:
    """Test CLI functionality."""
    
    @pytest.fixture
    def parser(self):
        """Create argument parser."""
        return create_parser()
    
    @pytest.fixture
    def temp_files(self):
        """Create temporary test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create chapter file
            chapter_file = temp_path / "chapters.txt"
            chapter_file.write_text("""
0:00:00.000 Opening
0:01:00.000 --CM
0:02:00.000 Content
            """.strip())
            
            # Create dummy video file
            video_file = temp_path / "video.mp4"
            video_file.touch()
            
            yield {
                'chapter_file': chapter_file,
                'video_file': video_file,
                'temp_dir': temp_path
            }
    
    def test_parse_basic_args(self, parser):
        """Test parsing basic arguments."""
        args = parser.parse_args(['chapters.txt', 'video.mp4'])
        
        assert args.chapter_file == 'chapters.txt'
        assert args.video_file == 'video.mp4'
        assert args.output is None
        assert not args.quiet
        assert not args.verbose
        assert not args.dry_run
    
    def test_parse_all_args(self, parser):
        """Test parsing all arguments."""
        args = parser.parse_args([
            'chapters.txt',
            'video.mp4',
            '-o', 'output.mp4',
            '-t', '/tmp/work',
            '-k',
            '-v',
            '--dry-run'
        ])
        
        assert args.output == 'output.mp4'
        assert args.temp_dir == '/tmp/work'
        assert args.keep_temp
        assert args.verbose
        assert args.dry_run
    
    def test_parse_quiet_verbose_exclusive(self, parser):
        """Test that quiet and verbose are mutually exclusive."""
        with pytest.raises(SystemExit):
            parser.parse_args(['chapters.txt', 'video.mp4', '-q', '-v'])
    
    @patch('video_chapter_trimmer.processor.VideoProcessor')
    @patch('video_chapter_trimmer.parser.ChapterParser')
    def test_trimmer_init(self, mock_parser_class, mock_processor_class, temp_files):
        """Test VideoChapterTrimmer initialization."""
        args = argparse.Namespace(
            chapter_file=str(temp_files['chapter_file']),
            video_file=str(temp_files['video_file']),
            output=None,
            temp_dir=None,
            keep_temp=False,
            quiet=False,
            verbose=False,
            dry_run=False
        )
        
        trimmer = VideoChapterTrimmer(args)
        
        assert trimmer.chapter_file == temp_files['chapter_file']
        assert trimmer.input_video == temp_files['video_file']
        assert trimmer.output_video.name == 'video_edited.mp4'
    
    @patch('video_chapter_trimmer.processor.VideoProcessor')
    @patch('video_chapter_trimmer.parser.ChapterParser')
    def test_trimmer_run_success(self, mock_parser_class, mock_processor_class, temp_files):
        """Test successful trimmer run."""
        # Setup mocks
        mock_parser = Mock()
        mock_parser.parse_file.return_value = [
            Mock(start=Mock(), end=Mock(), duration=Mock())
        ]
        mock_parser_class.return_value = mock_parser
        
        mock_processor = Mock()
        mock_processor_class.return_value = mock_processor
        
        args = argparse.Namespace(
            chapter_file=str(temp_files['chapter_file']),
            video_file=str(temp_files['video_file']),
            output=None,
            temp_dir=str(temp_files['temp_dir']),
            keep_temp=False,
            quiet=False,
            verbose=False,
            dry_run=False
        )
        
        trimmer = VideoChapterTrimmer(args)
        result = trimmer.run()
        
        assert result == 0
        mock_parser.parse_file.assert_called_once()
        mock_processor.extract_segment.assert_called()
        mock_processor.merge_segments.assert_called_once()
    
    @patch('video_chapter_trimmer.processor.VideoProcessor')
    @patch('video_chapter_trimmer.parser.ChapterParser')
    def test_trimmer_no_segments(self, mock_parser_class, mock_processor_class, temp_files):
        """Test trimmer with no segments to extract."""
        mock_parser = Mock()
        mock_parser.parse_file.return_value = []
        mock_parser_class.return_value = mock_parser
        
        args = argparse.Namespace(
            chapter_file=str(temp_files['chapter_file']),
            video_file=str(temp_files['video_file']),
            output=None,
            temp_dir=None,
            keep_temp=False,
            quiet=False,
            verbose=False,
            dry_run=False
        )
        
        trimmer = VideoChapterTrimmer(args)
        result = trimmer.run()
        
        assert result == 1
    
    def test_trimmer_missing_chapter_file(self, temp_files):
        """Test trimmer with missing chapter file."""
        args = argparse.Namespace(
            chapter_file='/nonexistent/chapters.txt',
            video_file=str(temp_files['video_file']),
            output=None,
            temp_dir=None,
            keep_temp=False,
            quiet=False,
            verbose=False,
            dry_run=False
        )
        
        trimmer = VideoChapterTrimmer(args)
        result = trimmer.run()
        
        assert result == 1
    
    @patch('sys.argv', ['video-chapter-trimmer', '--version'])
    def test_main_version(self):
        """Test main function with version flag."""
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
    
    @patch('sys.argv', ['video-chapter-trimmer', '--help'])
    def test_main_help(self):
        """Test main function with help flag."""
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
    
    def test_setup_logging_quiet(self):
        """Test logging setup with quiet mode."""
        import logging
        setup_logging(quiet=True, verbose=False)
        assert logging.getLogger().level == logging.WARNING
    
    def test_setup_logging_verbose(self):
        """Test logging setup with verbose mode."""
        import logging
        setup_logging(quiet=False, verbose=True)
        assert logging.getLogger().level == logging.DEBUG
    
    def test_format_size(self):
        """Test file size formatting."""
        test_cases = [
            (100, "100.0 B"),
            (1024, "1.0 KB"),
            (1024 * 1024, "1.0 MB"),
            (1024 * 1024 * 1024, "1.0 GB"),
            (1536 * 1024, "1.5 MB"),
        ]
        
        for size, expected in test_cases:
            result = VideoChapterTrimmer._format_size(size)
            assert result == expected