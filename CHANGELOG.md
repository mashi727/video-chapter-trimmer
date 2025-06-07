# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2024-01-03

### Added
- Automatic generation of adjusted chapter files for edited videos
- Chapter timestamps are recalculated to match the edited video
- `--no-chapters` option to disable chapter file generation
- Support for preserving chapter titles in the edited video

### Changed
- Default behavior now includes chapter file generation
- Output files now include both video and chapter file

## [1.1.0] - 2024-01-02

### Added
- Accurate cutting mode (`--accurate`) for better precision with keyframes
- Re-encoding mode (`--reencode`) for frame-accurate cuts
- Keyframe alignment validation and warnings
- Automatic encoding parameter detection based on source video
- Better handling of videos with B-frames and complex GOP structures

### Changed
- Improved segment extraction accuracy
- Better error messages for timing issues

### Fixed
- Chapter position drift due to keyframe alignment issues
- Incorrect cuts in videos with long GOP sizes

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

[Unreleased]: https://github.com/yourusername/video-chapter-trimmer/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/yourusername/video-chapter-trimmer/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/yourusername/video-chapter-trimmer/releases/tag/v1.0.0