# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2024-01-01

### Added
- Initial release
- Basic functionality to parse chapter files
- Extract video segments excluding marked sections (default: `--` prefix)
- Merge extracted segments into a single video file
- Command-line interface with various options:
  - Custom output filename
  - Temporary directory specification
  - Keep temporary files option
  - Quiet and verbose modes
  - Dry-run capability
- iOS-optimized video output
- Comprehensive error handling and logging
- Full test suite
- Documentation and examples

### Technical Details
- Stream copy (no re-encoding) for fast processing
- Support for any video format supported by ffmpeg
- Python 3.7+ compatibility
- No external Python dependencies (only requires ffmpeg)

[Unreleased]: https://github.com/yourusername/video-chapter-trimmer/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/yourusername/video-chapter-trimmer/releases/tag/v1.0.0