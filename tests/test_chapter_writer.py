"""Tests for chapter file writer."""

import pytest
from pathlib import Path
from datetime import timedelta
import tempfile

from video_chapter_trimmer.chapter_writer import ChapterWriter
from video_chapter_trimmer.models import Chapter, VideoSegment


class TestChapterWriter:
    """Test ChapterWriter class."""
    
    @pytest.fixture
    def writer(self):
        """Create a ChapterWriter instance."""
        return ChapterWriter()
    
    @pytest.fixture
    def sample_chapters(self):
        """Create sample chapters."""
        return [
            Chapter(timedelta(seconds=0), "Opening"),
            Chapter(timedelta(seconds=65, milliseconds=822), "--CM"),
            Chapter(timedelta(seconds=156, milliseconds=160), "Main Content"),
            Chapter(timedelta(minutes=26, seconds=25, milliseconds=64), "--CM"),
            Chapter(timedelta(minutes=28, seconds=25, milliseconds=179), "Ending"),
        ]
    
    @pytest.fixture
    def sample_segments(self):
        """Create sample segments."""
        return [
            VideoSegment(
                start=timedelta(seconds=0),
                end=timedelta(seconds=65, milliseconds=822)
            ),
            VideoSegment(
                start=timedelta(seconds=156, milliseconds=160),
                end=timedelta(minutes=26, seconds=25, milliseconds=64)
            ),
            VideoSegment(
                start=timedelta(minutes=28, seconds=25, milliseconds=179),
                end=None
            ),
        ]
    
    def test_generate_edited_chapters(self, writer, sample_chapters, sample_segments):
        """Test generating chapters for edited video."""
        edited_chapters = writer.generate_edited_chapters(
            sample_chapters, sample_segments
        )
        
        # Should have 3 chapters (excluding CMs)
        assert len(edited_chapters) == 3
        
        # First chapter should be at 0:00:00
        assert edited_chapters[0].timestamp == timedelta(0)
        assert edited_chapters[0].title == "Opening"
        
        # Second chapter should be adjusted
        # First segment duration: 65.822 seconds
        # Main Content was at 156.160, now at 0.000 (start of second segment)
        assert edited_chapters[1].timestamp == timedelta(seconds=65, milliseconds=822)
        assert edited_chapters[1].title == "Main Content"
        
        # Third chapter should be further adjusted
        # First segment: 65.822 seconds
        # Second segment: 26:25.064 - 2:36.160 = 23:48.904
        # Total before third: 65.822 + 1428.904 = 1494.726 seconds
        expected_third = timedelta(seconds=65, milliseconds=822) + \
                        timedelta(minutes=23, seconds=48, milliseconds=904)
        assert abs((edited_chapters[2].timestamp - expected_third).total_seconds()) < 0.001
        assert edited_chapters[2].title == "Ending"
    
    def test_write_chapter_file(self, writer):
        """Test writing chapters to file."""
        chapters = [
            Chapter(timedelta(0), "Start"),
            Chapter(timedelta(minutes=5, seconds=30, milliseconds=500), "Middle"),
            Chapter(timedelta(minutes=10), "End"),
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            writer.write_chapter_file(chapters, temp_path)
            
            content = temp_path.read_text()
            lines = content.strip().split('\n')
            
            assert len(lines) == 3
            assert lines[0] == "0:00:00.000 Start"
            assert lines[1] == "0:05:30.500 Middle"
            assert lines[2] == "0:10:00.000 End"
        finally:
            temp_path.unlink()
    
    def test_create_simple_chapters(self, writer, sample_segments):
        """Test creating simple chapters from segments."""
        chapters = writer.create_simple_chapters(sample_segments)
        
        assert len(chapters) == 3
        assert chapters[0].title == "Segment 1"
        assert chapters[1].title == "Segment 2"
        assert chapters[2].title == "Segment 3"
    
    def test_create_simple_chapters_with_titles(self, writer, sample_segments):
        """Test creating simple chapters with custom titles."""
        titles = ["Introduction", "Main Part", "Conclusion"]
        chapters = writer.create_simple_chapters(sample_segments, titles)
        
        assert len(chapters) == 3
        assert chapters[0].title == "Introduction"
        assert chapters[1].title == "Main Part"
        assert chapters[2].title == "Conclusion"
    
    def test_find_segment_for_timestamp(self, writer, sample_segments):
        """Test finding segment for a given timestamp."""
        # Timestamp in first segment
        idx = writer._find_segment_for_timestamp(
            timedelta(seconds=30), sample_segments
        )
        assert idx == 0
        
        # Timestamp in second segment
        idx = writer._find_segment_for_timestamp(
            timedelta(minutes=10), sample_segments
        )
        assert idx == 1
        
        # Timestamp in third segment (no end time)
        idx = writer._find_segment_for_timestamp(
            timedelta(minutes=30), sample_segments
        )
        assert idx == 2
        
        # Timestamp in excluded area
        idx = writer._find_segment_for_timestamp(
            timedelta(seconds=100), sample_segments
        )
        assert idx is None