"""Utility functions for video chapter trimmer."""

import re
from datetime import timedelta


class TimeParser:
    """Utility class for parsing and formatting time strings."""
    
    TIME_PATTERN = re.compile(r'^(\d+):(\d{2}):(\d{2})\.(\d{3})$')
    
    @classmethod
    def parse_timestamp(cls, time_str: str) -> timedelta:
        """
        Parse time string in format HH:MM:SS.mmm to timedelta.
        
        Args:
            time_str: Time string in format "HH:MM:SS.mmm"
            
        Returns:
            timedelta object
            
        Raises:
            ValueError: If time string format is invalid
        
        Examples:
            >>> TimeParser.parse_timestamp("0:00:05.151")
            timedelta(seconds=5, microseconds=151000)
        """
        match = cls.TIME_PATTERN.match(time_str)
        
        if not match:
            raise ValueError(
                f"Invalid time format: {time_str}. "
                f"Expected format: HH:MM:SS.mmm (e.g., 0:00:05.151)"
            )
        
        hours, minutes, seconds, milliseconds = map(int, match.groups())
        
        # Validate ranges
        if minutes >= 60 or seconds >= 60:
            raise ValueError(
                f"Invalid time values in {time_str}: "
                f"minutes and seconds must be < 60"
            )
        
        return timedelta(
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            milliseconds=milliseconds
        )
    
    @staticmethod
    def format_for_ffmpeg(td: timedelta) -> str:
        """
        Format timedelta for ffmpeg command.
        
        Args:
            td: timedelta object
            
        Returns:
            Formatted time string for ffmpeg (HH:MM:SS.mmm)
            
        Examples:
            >>> td = timedelta(hours=1, minutes=30, seconds=45, milliseconds=500)
            >>> TimeParser.format_for_ffmpeg(td)
            '01:30:45.500'
        """
        total_seconds = td.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"
    
    @staticmethod
    def format_for_chapter(td: timedelta) -> str:
        """
        Format timedelta for chapter file (original format).
        
        Args:
            td: timedelta object
            
        Returns:
            Formatted time string for chapter file (H:MM:SS.mmm)
            Single digit hours, 3 decimal places for milliseconds
            
        Examples:
            >>> td = timedelta(minutes=5, seconds=30, milliseconds=151)
            >>> TimeParser.format_for_chapter(td)
            '0:05:30.151'
            >>> td = timedelta(hours=1, minutes=30, seconds=45, milliseconds=500)
            >>> TimeParser.format_for_chapter(td)
            '1:30:45.500'
        """
        total_seconds = td.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = total_seconds % 60
        
        # Format with single digit hours and exactly 3 decimal places
        return f"{hours}:{minutes:02d}:{seconds:06.3f}"