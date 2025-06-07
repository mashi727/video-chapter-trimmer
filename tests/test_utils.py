"""Tests for utility functions."""

import pytest
from datetime import timedelta

from video_chapter_trimmer.utils import TimeParser


class TestTimeParser:
    """Test TimeParser utility class."""
    
    def test_parse_valid_timestamp(self):
        """Test parsing valid timestamp strings."""
        # Test various valid formats
        test_cases = [
            ("0:00:05.151", timedelta(seconds=5, milliseconds=151)),
            ("1:30:45.500", timedelta(hours=1, minutes=30, seconds=45, milliseconds=500)),
            ("12:59:59.999", timedelta(hours=12, minutes=59, seconds=59, milliseconds=999)),
            ("0:00:00.000", timedelta()),
        ]
        
        for time_str, expected in test_cases:
            result = TimeParser.parse_timestamp(time_str)
            assert result == expected
    
    def test_parse_invalid_timestamp_format(self):
        """Test parsing invalid timestamp formats."""
        invalid_formats = [
            "1:30:45",  # Missing milliseconds
            "1:30:45.50",  # Wrong milliseconds format
            "1:30",  # Missing seconds
            "01:30:45.500",  # Wrong hours format (should be single digit for < 10)
            "1:60:45.500",  # Invalid minutes
            "1:30:60.500",  # Invalid seconds
            "not a timestamp",
            "",
            "1:2:3.456",  # Minutes/seconds not zero-padded
        ]
        
        for time_str in invalid_formats:
            with pytest.raises(ValueError) as exc_info:
                TimeParser.parse_timestamp(time_str)
            assert "Invalid time" in str(exc_info.value)
    
    def test_format_for_ffmpeg(self):
        """Test formatting timedelta for ffmpeg."""
        test_cases = [
            (timedelta(seconds=5, milliseconds=151), "00:00:05.151"),
            (timedelta(hours=1, minutes=30, seconds=45, milliseconds=500), "01:30:45.500"),
            (timedelta(hours=12, minutes=59, seconds=59, milliseconds=999), "12:59:59.999"),
            (timedelta(), "00:00:00.000"),
            (timedelta(days=1, hours=2, minutes=30), "26:30:00.000"),  # > 24 hours
        ]
        
        for td, expected in test_cases:
            result = TimeParser.format_for_ffmpeg(td)
            assert result == expected
    
    def test_parse_and_format_roundtrip(self):
        """Test that parse and format are inverse operations."""
        time_strings = [
            "0:00:05.151",
            "1:30:45.500",
            "12:59:59.999",
            "0:00:00.000",
        ]
        
        for time_str in time_strings:
            td = TimeParser.parse_timestamp(time_str)
            formatted = TimeParser.format_for_ffmpeg(td)
            # Note: Hours might be zero-padded differently
            assert TimeParser.parse_timestamp(formatted) == td