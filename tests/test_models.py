"""Tests for data models."""

import pytest
from datetime import timedelta

from video_chapter_trimmer.models import VideoSegment


class TestVideoSegment:
    """Test VideoSegment class."""
    
    def test_create_segment_with_end(self):
        """Test creating a segment with start and end time."""
        start = timedelta(seconds=10)
        end = timedelta(seconds=30)
        segment = VideoSegment(start=start, end=end)
        
        assert segment.start == start
        assert segment.end == end
        assert segment.duration == timedelta(seconds=20)
    
    def test_create_segment_without_end(self):
        """Test creating a segment without end time."""
        start = timedelta(seconds=10)
        segment = VideoSegment(start=start)
        
        assert segment.start == start
        assert segment.end is None
        assert segment.duration is None
    
    def test_segment_repr(self):
        """Test string representation of VideoSegment."""
        start = timedelta(seconds=10)
        end = timedelta(seconds=30)
        
        segment_with_end = VideoSegment(start=start, end=end)
        assert "duration=" in repr(segment_with_end)
        
        segment_without_end = VideoSegment(start=start)
        assert "end=None" in repr(segment_without_end)
    
    def test_segment_equality(self):
        """Test segment equality comparison."""
        segment1 = VideoSegment(
            start=timedelta(seconds=10),
            end=timedelta(seconds=30)
        )
        segment2 = VideoSegment(
            start=timedelta(seconds=10),
            end=timedelta(seconds=30)
        )
        segment3 = VideoSegment(
            start=timedelta(seconds=10),
            end=timedelta(seconds=40)
        )
        
        assert segment1 == segment2
        assert segment1 != segment3