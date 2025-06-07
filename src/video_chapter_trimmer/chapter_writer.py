"""Chapter file writer for edited videos."""

from datetime import timedelta
from pathlib import Path
from typing import List

from .models import Chapter, VideoSegment
from .utils import TimeParser


class ChapterWriter:
    """Generates chapter files for edited videos."""
    
    def __init__(self, exclude_prefix: str = "--"):
        """
        Initialize ChapterWriter.
        
        Args:
            exclude_prefix: Prefix that marks excluded chapters
        """
        self.exclude_prefix = exclude_prefix
    
    def generate_edited_chapters(self, 
                                original_chapters: List[Chapter],
                                segments: List[VideoSegment]) -> List[Chapter]:
        """
        Generate new chapter list for edited video.
        
        Args:
            original_chapters: Original chapters from source video
            segments: Segments that were extracted
            
        Returns:
            List of chapters adjusted for the edited video
        """
        edited_chapters = []
        current_offset = timedelta()
        
        for chapter in original_chapters:
            # Skip chapters that are excluded
            if chapter.title.startswith(self.exclude_prefix):
                continue
            
            # Find which segment this chapter belongs to
            segment_index = self._find_segment_for_timestamp(
                chapter.timestamp, segments
            )
            
            if segment_index is not None:
                # Calculate the new timestamp
                # Sum of all previous segment durations
                new_timestamp = timedelta()
                for i in range(segment_index):
                    if segments[i].duration:
                        new_timestamp += segments[i].duration
                
                # Add offset within current segment
                offset_in_segment = chapter.timestamp - segments[segment_index].start
                new_timestamp += offset_in_segment
                
                edited_chapters.append(Chapter(
                    timestamp=new_timestamp,
                    title=chapter.title
                ))
        
        return edited_chapters
    
    def _find_segment_for_timestamp(self, 
                                   timestamp: timedelta,
                                   segments: List[VideoSegment]) -> int:
        """
        Find which segment a timestamp belongs to.
        
        Args:
            timestamp: Timestamp to check
            segments: List of segments
            
        Returns:
            Segment index or None if not in any segment
        """
        for i, segment in enumerate(segments):
            if segment.end is None:
                # Last segment - check if timestamp is after start
                if timestamp >= segment.start:
                    return i
            else:
                # Check if timestamp is within segment
                if segment.start <= timestamp < segment.end:
                    return i
        
        return None
    
    def write_chapter_file(self, 
                          chapters: List[Chapter],
                          output_path: Path) -> None:
        """
        Write chapters to a file.
        
        Args:
            chapters: List of chapters to write
            output_path: Path to output file
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            for chapter in chapters:
                # Use the chapter format (H:MM:SS.mmm)
                timestamp_str = TimeParser.format_for_chapter(chapter.timestamp)
                f.write(f"{timestamp_str} {chapter.title}\n")
    
    def create_simple_chapters(self, 
                              segments: List[VideoSegment],
                              segment_titles: List[str] = None) -> List[Chapter]:
        """
        Create simple chapters based on segments.
        
        Args:
            segments: List of segments
            segment_titles: Optional titles for each segment
            
        Returns:
            List of chapters
        """
        chapters = []
        current_time = timedelta()
        
        for i, segment in enumerate(segments):
            if segment_titles and i < len(segment_titles):
                title = segment_titles[i]
            else:
                title = f"Segment {i + 1}"
            
            chapters.append(Chapter(
                timestamp=current_time,
                title=title
            ))
            
            if segment.duration:
                current_time += segment.duration
        
        return chapters