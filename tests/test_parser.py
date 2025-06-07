"""Tests for chapter file parser."""

import pytest
from pathlib import Path
from datetime import timedelta
import tempfile

from video_chapter_trimmer.parser import ChapterParser
from video_chapter_trimmer.models import VideoSegment


class TestChapterParser:
    """Test ChapterParser class."""
    
    @pytest.fixture
    def parser(self):
        """Create a ChapterParser instance."""
        return ChapterParser()
    
    @pytest.fixture
    def temp_chapter_file(self):
        """Create a temporary chapter file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_path = Path(f.name)
            yield temp_path
        temp_path.unlink()
    
    def test_parse_simple_file(self, parser, temp_chapter_file):
        """Test parsing a simple chapter file."""
        content = """
0:00:05.151 Opening
0:01:05.822 --CM
0:02:36.160 Main Content
0:26:25.064 --CM
0:28:25.179 Ending
        """
        temp_chapter_file.write_text(content.strip())
        
        segments = parser.parse_file(temp_chapter_file)
        
        assert len(segments) == 3
        
        # First segment: Opening
        assert segments[0].start == timedelta(seconds=5, milliseconds=151)
        assert segments[0].end == timedelta(minutes=1, seconds=5, milliseconds=822)
        
        # Second segment: Main Content
        assert segments[1].start == timedelta(minutes=2, seconds=36, milliseconds=160)
        assert segments[1].end == timedelta(minutes=26, seconds=25, milliseconds=64)
        
        # Third segment: Ending (no end time)
        assert segments[2].start == timedelta(minutes=28, seconds=25, milliseconds=179)
        assert segments[2].end is None
    
    def test_parse_file_starting_with_cm(self, parser, temp_chapter_file):
        """Test parsing file that starts with CM."""
        content = """
0:00:00.000 --Pre-roll Ad
0:00:30.000 Actual Content
0:05:00.000 --Mid-roll Ad
0:05:30.000 More Content
        """
        temp_chapter_file.write_text(content.strip())
        
        segments = parser.parse_file(temp_chapter_file)
        
        assert len(segments) == 2
        assert segments[0].start == timedelta(seconds=30)
        assert segments[1].start == timedelta(minutes=5, seconds=30)
    
    def test_parse_file_all_content(self, parser, temp_chapter_file):
        """Test parsing file with no CMs."""
        content = """
0:00:00.000 Part 1
0:10:00.000 Part 2
0:20:00.000 Part 3
        """
        temp_chapter_file.write_text(content.strip())
        
        segments = parser.parse_file(temp_chapter_file)
        
        assert len(segments) == 1
        assert segments[0].start == timedelta()
        assert segments[0].end is None
    
    def test_parse_file_all_cm(self, parser, temp_chapter_file):
        """Test parsing file with only CMs."""
        content = """
0:00:00.000 --CM 1
0:10:00.000 --CM 2
0:20:00.000 --CM 3
        """
        temp_chapter_file.write_text(content.strip())
        
        segments = parser.parse_file(temp_chapter_file)
        
        assert len(segments) == 0
    
    def test_parse_empty_file(self, parser, temp_chapter_file):
        """Test parsing empty file."""
        temp_chapter_file.write_text("")
        
        with pytest.raises(ValueError) as exc_info:
            parser.parse_file(temp_chapter_file)
        assert "empty" in str(exc_info.value).lower()
    
    def test_parse_invalid_line_format(self, parser, temp_chapter_file):
        """Test parsing file with invalid line format."""
        content = """
0:00:05.151 Opening
This is not a valid line
0:02:36.160 Main Content
        """
        temp_chapter_file.write_text(content.strip())
        
        with pytest.raises(ValueError) as exc_info:
            parser.parse_file(temp_chapter_file)
        assert "Error at line 2" in str(exc_info.value)
    
    def test_parse_nonexistent_file(self, parser):
        """Test parsing non-existent file."""
        with pytest.raises(FileNotFoundError):
            parser.parse_file(Path("/nonexistent/file.txt"))
    
    def test_custom_exclude_prefix(self, temp_chapter_file):
        """Test using custom exclude prefix."""
        parser = ChapterParser(exclude_prefix="SKIP:")
        
        content = """
0:00:00.000 Opening
0:01:00.000 SKIP:Advertisement
0:02:00.000 Content
0:03:00.000 SKIP:Another Ad
0:04:00.000 Ending
        """
        temp_chapter_file.write_text(content.strip())
        
        segments = parser.parse_file(temp_chapter_file)
        
        assert len(segments) == 3
        assert segments[0].end == timedelta(minutes=1)
        assert segments[1].start == timedelta(minutes=2)
        assert segments[1].end == timedelta(minutes=3)
        assert segments[2].start == timedelta(minutes=4)