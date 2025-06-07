"""Command-line interface for video chapter trimmer."""

import sys
import logging
import shutil
import tempfile
from datetime import timedelta
from pathlib import Path
from typing import List
import argparse

from . import __version__, __description__
from .models import Chapter
from .parser import ChapterParser
from .processor import VideoProcessor
from .chapter_writer import ChapterWriter

logger = logging.getLogger(__name__)


class VideoChapterTrimmer:
    """Main application class for video chapter trimming."""
    
    def __init__(self, args: argparse.Namespace):
        """
        Initialize VideoChapterTrimmer.
        
        Args:
            args: Parsed command-line arguments
        """
        self.args = args
        self.parser = ChapterParser()
        self.processor = VideoProcessor(
            verbose=args.verbose, 
            dry_run=args.dry_run,
            accurate=args.accurate,
            reencode=args.reencode,
            gpu=args.gpu,
            split_safe=args.split_safe
        )
        self.chapter_writer = ChapterWriter()
        
        # Setup paths
        self.chapter_file = Path(args.chapter_file)
        self.input_video = Path(args.video_file)
        self._setup_output_path()
        self._setup_temp_dir()
    
    def _setup_output_path(self):
        """Setup output file path."""
        if self.args.output:
            self.output_video = Path(self.args.output)
        else:
            stem = self.input_video.stem
            suffix = self.input_video.suffix
            self.output_video = self.input_video.parent / f"{stem}_edited{suffix}"
        
        # Setup chapter output path
        self.output_chapter = self.output_video.with_suffix('.txt')
    
    def _setup_temp_dir(self):
        """Setup temporary directory."""
        if self.args.temp_dir:
            self.temp_dir = Path(self.args.temp_dir)
            self.temp_dir.mkdir(exist_ok=True)
            self._temp_created = False
        else:
            self.temp_dir = Path(tempfile.mkdtemp(prefix="video_trimmer_"))
            self._temp_created = True
    
    def run(self) -> int:
        """
        Execute the main processing workflow.
        
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            # Validate input files
            if not self.chapter_file.exists():
                logger.error(f"Chapter file not found: {self.chapter_file}")
                return 1
            
            if not self.input_video.exists():
                logger.error(f"Video file not found: {self.input_video}")
                return 1
            
            # Parse chapters
            if not self.args.quiet:
                logger.info(f"Parsing chapter file: {self.chapter_file}")
            
            segments, chapters = self.parser.parse_file(self.chapter_file)
            
            # Split mode - split video by chapters
            if self.args.split:
                return self._run_split_mode(chapters)
            
            if not segments:
                logger.warning("No segments found to extract.")
                return 1
            
            if not self.args.quiet:
                logger.info(f"Found {len(segments)} segments to extract")
                if self.args.verbose:
                    for i, seg in enumerate(segments):
                        logger.debug(f"  Segment {i+1}: {seg}")
            
            # Validate segments if not in fast mode
            if self.args.accurate or self.args.reencode:
                if not self.args.quiet:
                    logger.info("Validating segment keyframe alignment...")
                
                warnings = self.processor.validate_segments(self.input_video, segments)
                if warnings:
                    for warning in warnings:
                        logger.warning(warning)
                    
                    if not self.args.accurate and not self.args.reencode:
                        logger.info("Tip: Use --accurate or --reencode for precise cuts")
            
            # Check if output already exists
            if self.output_video.exists() and not self.args.dry_run:
                if not self._confirm_overwrite():
                    logger.info("Operation cancelled.")
                    return 0
            
            # Check if chapter output already exists
            if self.output_chapter.exists() and not self.args.dry_run:
                if not self.args.quiet:
                    logger.debug(f"Chapter file will be overwritten: {self.output_chapter}")
            
            # Extract segments
            segment_files = []
            for i, segment in enumerate(segments):
                if not self.args.quiet:
                    mode = "re-encoding" if self.args.reencode else "extracting"
                    logger.info(f"{mode.capitalize()} segment {i+1}/{len(segments)}")
                
                output_file = self.temp_dir / f"segment_{i:03d}.mp4"
                
                # Pass chapters if split-safe mode is enabled
                segment_chapters = None
                if self.args.split_safe:
                    # Filter chapters that belong to this segment
                    segment_chapters = [
                        ch for ch in chapters
                        if segment.start <= ch.timestamp and 
                           (segment.end is None or ch.timestamp < segment.end)
                    ]
                
                self.processor.extract_segment(
                    self.input_video, 
                    output_file, 
                    segment,
                    segment_chapters
                )
                segment_files.append(output_file)
            
            # Merge segments
            if not self.args.quiet:
                logger.info("Merging segments...")
            
            self.processor.merge_segments(segment_files, self.output_video)
            
            # Generate and write new chapter file
            if not self.args.no_chapters:
                if not self.args.quiet:
                    logger.info("Generating chapter file for edited video...")
                
                edited_chapters = self.chapter_writer.generate_edited_chapters(
                    chapters, segments
                )
                
                if edited_chapters:
                    if not self.args.dry_run:
                        self.chapter_writer.write_chapter_file(
                            edited_chapters, self.output_chapter
                        )
                    
                    if not self.args.quiet:
                        logger.info(f"Chapter file saved to: {self.output_chapter}")
                        if self.args.verbose:
                            logger.debug(f"Generated {len(edited_chapters)} chapters")
                else:
                    if not self.args.quiet:
                        logger.warning("No chapters to write for edited video")
            
            if not self.args.quiet:
                logger.info(f"Success! Output saved to: {self.output_video}")
                
                # Show file size comparison if verbose
                if self.args.verbose and not self.args.dry_run:
                    self._show_file_sizes()
            
            return 0
            
        except KeyboardInterrupt:
            logger.info("\nOperation cancelled by user.")
            return 130
        except Exception as e:
            logger.error(f"Error: {e}")
            if self.args.verbose:
                logger.exception("Detailed error information:")
            return 1
        finally:
            self._cleanup()
    
    def _run_split_mode(self, chapters: List['Chapter']) -> int:
        """
        Run in split mode - split video by chapters.
        
        Args:
            chapters: List of chapters to split by
            
        Returns:
            Exit code
        """
        try:
            # Filter out excluded chapters
            valid_chapters = [ch for ch in chapters if not ch.title.startswith("--")]
            
            if not valid_chapters:
                logger.warning("No chapters found to split (all chapters are excluded).")
                return 1
            
            if not self.args.quiet:
                logger.info(f"Found {len(valid_chapters)} chapters to extract")
            
            # Create output directory
            if self.args.output:
                output_dir = Path(self.args.output)
            else:
                # Use video filename as directory name
                output_dir = self.input_video.parent / self.input_video.stem
            
            if not self.args.dry_run:
                output_dir.mkdir(exist_ok=True)
            
            if not self.args.quiet:
                logger.info(f"Output directory: {output_dir}")
            
            # Split video by chapters
            output_files = self.processor.split_video_by_chapters(
                self.input_video,
                chapters,
                output_dir,
                self.args.split_pattern or "{num:02d}_{title}"
            )
            
            if not self.args.quiet and not self.args.dry_run:
                logger.info(f"Successfully created {len(output_files)} chapter files")
                if self.args.verbose:
                    for file in output_files:
                        logger.debug(f"  - {file.name}")
            
            return 0
            
        except Exception as e:
            logger.error(f"Error during split: {e}")
            if self.args.verbose:
                logger.exception("Detailed error information:")
            return 1
    
    def _confirm_overwrite(self) -> bool:
        """Ask user for confirmation to overwrite existing file."""
        response = input(f"Output file '{self.output_video}' already exists. Overwrite? [y/N]: ")
        return response.lower() in ('y', 'yes')
    
    def _show_file_sizes(self):
        """Display file size comparison."""
        try:
            original_size = self.input_video.stat().st_size
            new_size = self.output_video.stat().st_size
            reduction = (1 - new_size / original_size) * 100
            
            logger.info(f"Original size: {self._format_size(original_size)}")
            logger.info(f"New size: {self._format_size(new_size)}")
            logger.info(f"Size reduction: {reduction:.1f}%")
        except Exception:
            pass
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format byte size to human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def _cleanup(self):
        """Clean up temporary files."""
        if self._temp_created and not self.args.keep_temp:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                if self.args.verbose:
                    logger.debug(f"Cleaned up temporary directory: {self.temp_dir}")


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        prog='video-chapter-trimmer',
        description=__description__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s chapters.txt video.mp4
  %(prog)s chapters.txt video.mp4 -o edited.mp4
  %(prog)s chapters.txt video.mp4 --dry-run
  %(prog)s chapters.txt video.mp4 -v --keep-temp
  %(prog)s chapters.txt video.mp4 --accurate  # More precise cuts
  %(prog)s chapters.txt video.mp4 --reencode  # Most accurate (slow)
  %(prog)s chapters.txt video.mp4 --gpu auto  # Auto-detect GPU
  %(prog)s chapters.txt video.mp4 --gpu videotoolbox  # macOS M1/M2/M3
  %(prog)s chapters.txt video.mp4 --reencode --gpu nvenc  # NVIDIA GPU
  %(prog)s chapters.txt video.mp4 --split  # Split into chapter files
  %(prog)s chapters.txt video.mp4 --split -o my_chapters  # Custom output dir

Chapter file format:
  0:00:05.151 Opening
  0:01:05.822 --CM
  0:02:36.160 Main Content
  0:26:25.064 --CM
  0:28:25.179 Ending

Lines starting with '--' are excluded from the output.
        """
    )
    
    # Positional arguments
    parser.add_argument('chapter_file', 
                       help='Chapter file with timestamps')
    parser.add_argument('video_file', 
                       help='Input video file')
    
    # Optional arguments
    parser.add_argument('-o', '--output',
                       help='Output filename (default: <input>_edited.<ext>) or directory for --split mode')
    parser.add_argument('-t', '--temp-dir',
                       help='Temporary directory (default: auto-generated)')
    parser.add_argument('-k', '--keep-temp',
                       action='store_true',
                       help='Keep temporary files after processing')
    
    # Output control
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument('-q', '--quiet',
                            action='store_true',
                            help='Suppress progress messages')
    output_group.add_argument('-v', '--verbose',
                            action='store_true',
                            help='Show detailed output')
    
    # Processing options
    parser.add_argument('--dry-run',
                       action='store_true',
                       help='Show what would be done without executing')
    
    parser.add_argument('--accurate',
                       action='store_true',
                       help='Use accurate seeking (slower but more precise)')
    
    parser.add_argument('--reencode',
                       action='store_true',
                       help='Force re-encoding for precise cuts (slowest but most accurate)')
    
    parser.add_argument('--no-chapters',
                       action='store_true',
                       help='Do not generate chapter file for edited video')
    
    # Hardware acceleration
    parser.add_argument('--gpu',
                       choices=['auto', 'videotoolbox', 'nvenc', 'qsv', 'amf'],
                       help='Use GPU acceleration for encoding (auto-detect or specify)')
    
    parser.add_argument('--split-safe',
                       action='store_true',
                       help='Optimize encoding for future splitting (adds keyframes)')
    
    # Split mode
    parser.add_argument('--split',
                       action='store_true',
                       help='Split video into separate files by chapters')
    
    parser.add_argument('--split-pattern',
                       help='Pattern for split filenames (default: "{num:02d}_{title}")')
    
    # Version
    parser.add_argument('--version',
                       action='version',
                       version=f'%(prog)s {__version__}')
    
    return parser


def setup_logging(quiet: bool, verbose: bool):
    """Configure logging based on verbosity settings."""
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        if verbose else '%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Configure logging
    setup_logging(args.quiet, args.verbose)
    
    # Run application
    app = VideoChapterTrimmer(args)
    sys.exit(app.run())


if __name__ == "__main__":
    main()