# Video Chunker

CLI tool that downloads videos from URLs and splits them into 30-second chunks optimized for social media reels (YouTube Shorts, Instagram Reels, Facebook Reels, TikTok).

## Features

- 📥 Download videos from any URL (YouTube, Twitter, etc.) using yt-dlp
- ✂️ Split videos into 30-second chunks (configurable)
- 🎨 Transcode to platform-specific formats (9:16 aspect ratio, proper encoding)
- 🤖 Smart face detection for intelligent cropping (fills entire screen, no black bars)
- 📱 Support for YouTube, Instagram, Facebook, and TikTok

## Requirements

- Python 3.10+
- FFmpeg (must be installed system-wide)

### Installing FFmpeg

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html

## Installation

```bash
# Clone repository
cd video-testing

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Linux/macOS
# OR
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic usage (process for all platforms):
```bash
python -m videochunker "https://youtube.com/watch?v=..."
```

### Specify a platform:
```bash
python -m videochunker "VIDEO_URL" --platform youtube
python -m videochunker "VIDEO_URL" --platform instagram
python -m videochunker "VIDEO_URL" --platform facebook
python -m videochunker "VIDEO_URL" --platform tiktok
```

### Custom output directory:
```bash
python -m videochunker "VIDEO_URL" --output ./my-reels
```

### Custom chunk duration:
```bash
python -m videochunker "VIDEO_URL" --duration 60
```

### Limit number of chunks (default is 5):
```bash
python -m videochunker "VIDEO_URL" --max-chunks 10
```

### Disable smart face detection (use center crop instead):
```bash
python -m videochunker "VIDEO_URL" --no-smart-crop
```

### Keep temporary files:
```bash
python -m videochunker "VIDEO_URL" --keep-temp
```

## Output Structure

```
output/
├── youtube_shorts/
│   ├── video_chunk_001_youtube_shorts.mp4
│   ├── video_chunk_002_youtube_shorts.mp4
│   └── ...
├── instagram_reels/
│   ├── video_chunk_001_instagram_reels.mp4
│   └── ...
├── facebook_reels/
│   └── ...
└── tiktok/
    └── ...
```

## Smart Cropping

By default, the tool uses **face detection** to intelligently crop videos:

1. **Detects faces** in the video using OpenCV's Haar Cascade classifier
2. **Calculates optimal crop region** centered on detected faces
3. **Fills entire 9:16 screen** - no black bars!
4. **Falls back to center crop** if no faces are detected

To disable smart cropping and use simple center crop instead:
```bash
python -m videochunker "VIDEO_URL" --no-smart-crop
```

## Platform Specifications

| Platform  | Aspect Ratio | Max Duration | Resolution | Format |
|-----------|--------------|--------------|------------|--------|
| YouTube   | 9:16         | 60s          | 1080x1920  | MP4/H.264 |
| Instagram | 9:16         | 90s          | 1080x1920  | MP4/H.264 |
| Facebook  | 9:16         | 60s          | 1080x1920  | MP4/H.264 |
| TikTok    | 9:16         | 60s          | 1080x1920  | MP4/H.264 |

## Development

This project was developed with [Claude Code](https://claude.ai/code), Anthropic's AI-powered coding assistant. Claude was instrumental in:
- Architecture design and planning
- Implementation of all core modules
- Face detection integration
- CLI interface development
- Testing and refinement

## License

MIT
