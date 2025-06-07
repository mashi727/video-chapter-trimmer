"""Command-line interface for video chapter trimmer."""

import sys
import logging
import shutil
import tempfile
from pathlib import Path
import argparse

from . import __version__, __description__
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
            reencode=args.reencode
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
                self.processor.extract_segment(
                    self.input_video, 
                    output_file, 
                    segment
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
                       help='Output filename (default: <input>_edited.<ext>)')
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