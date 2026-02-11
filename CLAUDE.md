# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CLI tool that processes videos (from URLs or local files) and splits them into 30-second chunks optimized for social media reels (YouTube Shorts, Instagram Reels, Facebook Reels, TikTok). Features smart face detection for intelligent cropping that fills the entire 9:16 screen.

## Tech Stack

- Python 3.10+
- FFmpeg (system dependency, called via subprocess or ffmpeg-python)
- OpenCV (opencv-python) for face detection
- Click for CLI

## Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run CLI (default: first 5 chunks, all platforms)
# Input can be a URL or local file path
python -m videochunker <video_input>

# Examples:
# python -m videochunker "https://youtube.com/watch?v=..."
# python -m videochunker "/path/to/video.mp4"
# python -m videochunker "./my-video.mkv"

# Options:
# --platform, -p: Target platform (youtube|instagram|facebook|tiktok|all) [default: all]
# --output, -o: Output directory [default: ./output]
# --duration, -d: Chunk duration in seconds [default: 30]
# --max-chunks, -m: Maximum chunks to create [default: 5]
# --smart-crop/--no-smart-crop: Enable face detection for smart cropping [default: enabled]
# --hflip/--no-hflip: Apply horizontal flip effect to output videos [default: enabled]
# --keep-temp: Keep temporary files

# Supported video formats: MP4, MKV, AVI, MOV, WebM, FLV, WMV, M4V

# Run tests
pytest

# Lint
ruff check .
```

## Architecture

```
videochunker/
├── __main__.py       # CLI entry point
├── downloader.py     # Download video from URL (yt-dlp)
├── chunker.py        # Split video into 30s segments using FFmpeg
├── face_detector.py  # Face detection using OpenCV for smart cropping
├── transcoder.py     # Platform-specific encoding (aspect ratio, bitrate, codec)
└── platforms.py      # Platform specs and presets
```

## Smart Cropping

The tool uses OpenCV's Haar Cascade classifier to detect faces in video frames:
1. Extracts middle frame from each video chunk
2. Detects faces using `haarcascade_frontalface_default.xml`
3. Calculates crop region centered on detected faces
4. Falls back to center crop if no faces detected

## Platform Output Specs

| Platform  | Aspect Ratio | Max Duration | Resolution | Format |
|-----------|--------------|--------------|------------|--------|
| YouTube   | 9:16         | 60s          | 1080x1920  | MP4/H.264 |
| Instagram | 9:16         | 90s          | 1080x1920  | MP4/H.264 |
| Facebook  | 9:16         | 90s          | 1080x1920  | MP4/H.264 |
| TikTok    | 9:16         | 60s          | 1080x1920  | MP4/H.264 |

## Key Dependencies

- `yt-dlp`: Video downloading from URLs
- `ffmpeg-python` or subprocess calls to `ffmpeg`: Video processing
- `opencv-python`: Face detection for smart cropping
- `click`: CLI framework
- FFmpeg must be installed system-wide (`apt install ffmpeg` or `brew install ffmpeg`)
