"""
Video Chapter Trimmer

A command-line tool to extract and merge video segments based on chapter markers,
excluding segments marked with '--' prefix (e.g., commercials).
"""

# Version information
__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# Package metadata
__title__ = "video-chapter-trimmer"
__description__ = "Extract and merge video segments based on chapter markers"
__url__ = "https://github.com/yourusername/video-chapter-trimmer"
__license__ = "MIT"
__copyright__ = "Copyright 2024 Your Name"

# Import main components
from .models import VideoSegment, Chapter
from .utils import TimeParser
from .parser import ChapterParser
from .processor import VideoProcessor
from .chapter_writer import ChapterWriter

# Public API
__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__email__",
    "__title__",
    "__description__",
    "__url__",
    "__license__",
    "__copyright__",
    
    # Classes
    "VideoSegment",
    "Chapter",
    "TimeParser",
    "ChapterParser",
    "VideoProcessor",
    "ChapterWriter",
]

# Convenience imports for CLI
try:
    from .cli import VideoChapterTrimmer, main
    __all__.extend(["VideoChapterTrimmer", "main"])
except ImportError:
    # CLI might not be available in all contexts
    pass