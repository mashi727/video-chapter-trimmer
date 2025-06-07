"""Chapter file parser for video chapter trimmer."""

import re
from pathlib import Path
from typing import List, Tuple

from .models import VideoSegment
from .utils import TimeParser


class ChapterParser:
    """Parser for chapter files."""
    
    LINE_PATTERN = re.compile(r'^(\d+:\d{2}:\d{2}\.\d{3})\s+(.*)$')
    
    def __init__(self, exclude_prefix: str = "--"):
        """
        Initialize ChapterParser.
        
        Args:
            exclude_prefix: Prefix that marks chapters to exclude (default: "--")
        """
        self.exclude_prefix = exclude_prefix
    
    def parse_file(self, filepath: Path) -> List[VideoSegment]:
        """
        Parse chapter file and extract segments.
        
        Args:
            filepath: Path to chapter file
            
        Returns:
            List of VideoSegment objects
            
        Raises:
            FileNotFoundError: If chapter file doesn't exist
            ValueError: If file format is invalid
        """
        if not filepath.exists():
            raise FileNotFoundError(f"Chapter file not found: {filepath}")
        
        if not filepath.is_file():
            raise ValueError(f"Path is not a file: {filepath}")
        
        segments = []
        current_start = None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        if not lines:
            raise ValueError(f"Chapter file is empty: {filepath}")
        
        for i, line in enumerate(lines, 1):
            try:
                timestamp, title = self._parse_line(line)
            except ValueError as e:
                raise ValueError(f"Error at line {i}: {e}")
            
            if title.startswith(self.exclude_prefix):
                # End current segment if exists
                if current_start is not None:
                    segments.append(VideoSegment(
                        start=current_start,
                        end=TimeParser.parse_timestamp(timestamp)
                    ))
                    current_start = None
            else:
                # Start new segment if not in one
                if current_start is None:
                    current_start = TimeParser.parse_timestamp(timestamp)
        
        # Handle unclosed segment
        if current_start is not None:
            segments.append(VideoSegment(start=current_start))
        
        return segments
    
    def _parse_line(self, line: str) -> Tuple[str, str]:
        """
        Parse a single line from chapter file.
        
        Args:
            line: Line to parse
            
        Returns:
            Tuple of (timestamp, title)
            
        Raises:
            ValueError: If line format is invalid
        """
        match = self.LINE_PATTERN.match(line)
        if not match:
            raise ValueError(
                f"Invalid line format: '{line}'. "
                f"Expected format: 'HH:MM:SS.mmm Title'"
            )
        return match.groups()
