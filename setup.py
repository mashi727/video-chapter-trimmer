"""Setup configuration for video-chapter-trimmer."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="video-chapter-trimmer",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Extract and merge video segments based on chapter markers",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/video-chapter-trimmer",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Video",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        # No external dependencies required
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=22.0",
            "flake8>=5.0",
            "mypy>=1.0",
            "pre-commit>=3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "video-chapter-trimmer=video_chapter_trimmer.cli:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/yourusername/video-chapter-trimmer/issues",
        "Source": "https://github.com/yourusername/video-chapter-trimmer",
    },
)