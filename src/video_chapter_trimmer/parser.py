"""Chapter file parser for video chapter trimmer."""

import re
from pathlib import Path
from typing import List, Tuple, Dict

from .models import VideoSegment, Chapter
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
    
    def parse_file(self, filepath: Path) -> Tuple[List[VideoSegment], List[Chapter]]:
        """
        Parse chapter file and extract segments and chapters.
        
        Args:
            filepath: Path to chapter file
            
        Returns:
            Tuple of (segments, chapters) where:
            - segments: List of VideoSegment objects to extract
            - chapters: List of all Chapter objects from the file
            
        Raises:
            FileNotFoundError: If chapter file doesn't exist
            ValueError: If file format is invalid
        """
        if not filepath.exists():
            raise FileNotFoundError(f"Chapter file not found: {filepath}")
        
        if not filepath.is_file():
            raise ValueError(f"Path is not a file: {filepath}")
        
        segments = []
        chapters = []
        current_start = None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        if not lines:
            raise ValueError(f"Chapter file is empty: {filepath}")
        
        for i, line in enumerate(lines, 1):
            try:
                timestamp, title = self._parse_line(line)
                timestamp_td = TimeParser.parse_timestamp(timestamp)
                
                # Store all chapters
                chapters.append(Chapter(timestamp=timestamp_td, title=title))
                
                if title.startswith(self.exclude_prefix):
                    # End current segment if exists
                    if current_start is not None:
                        segments.append(VideoSegment(
                            start=current_start,
                            end=timestamp_td
                        ))
                        current_start = None
                else:
                    # Start new segment if not in one
                    if current_start is None:
                        current_start = timestamp_td
            except ValueError as e:
                raise ValueError(f"Error at line {i}: {e}")
        
        # Handle unclosed segment
        if current_start is not None:
            segments.append(VideoSegment(start=current_start))
        
        return segments, chapters
    
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