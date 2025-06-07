"""Data models for video chapter trimmer."""

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional


@dataclass
class VideoSegment:
    """Represents a video segment with start and optional end time."""
    start: timedelta
    end: Optional[timedelta] = None
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate segment duration if end time is available."""
        return self.end - self.start if self.end else None
    
    def __repr__(self) -> str:
        """String representation of VideoSegment."""
        if self.end:
            return f"VideoSegment(start={self.start}, end={self.end}, duration={self.duration})"
        return f"VideoSegment(start={self.start}, end=None)"
