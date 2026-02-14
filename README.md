# Video Chunker

CLI tool that processes videos (from URLs or local files) and splits them into 30-second chunks optimized for social media reels (YouTube Shorts, Instagram Reels, Facebook Reels, TikTok).

## Features

- 📥 Download videos from any URL (YouTube, Twitter, etc.) using yt-dlp
- 📁 Process local video files directly (no download needed)
- ✂️ Split videos into 30-second chunks (configurable)
- 🎨 Transcode to platform-specific formats (9:16 aspect ratio, proper encoding)
- 🤖 Smart cropping with **MediaPipe** (faces) or **YOLO** (people) detection
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

**From URL:**
```bash
python -m videochunker "https://youtube.com/watch?v=..."
```

**From local file:**
```bash
python -m videochunker "/path/to/video.mp4"
python -m videochunker "./my-video.mkv"
```

**Supported video formats:** MP4, MKV, AVI, MOV, WebM, FLV, WMV, M4V

### Specify a platform:
```bash
# URL input
python -m videochunker "https://youtube.com/watch?v=..." --platform youtube

# Local file input
python -m videochunker "/home/user/video.mp4" --platform instagram
python -m videochunker "./video.mkv" --platform facebook
```

### Custom output directory:
```bash
python -m videochunker "VIDEO_INPUT" --output ./my-reels
```

### Custom chunk duration:
```bash
python -m videochunker "VIDEO_INPUT" --duration 60
```

### Limit number of chunks (default is 5):
```bash
python -m videochunker "VIDEO_INPUT" --max-chunks 10
```

### Choose crop method (MediaPipe or YOLO):
```bash
# MediaPipe (default) - Fast, good for faces/talking heads
python -m videochunker "VIDEO_INPUT" --crop-method mediapipe

# YOLO - Advanced, better for full-body/action/sports
python -m videochunker "VIDEO_INPUT" --crop-method yolo
```

### Disable smart cropping (use center crop):
```bash
python -m videochunker "VIDEO_INPUT" --no-smart-crop
```

### Keep temporary files:
```bash
python -m videochunker "VIDEO_INPUT" --keep-temp
```

### Complete example with all options:
```bash
python -m videochunker "/movies/inception.mp4" \
  --platform tiktok \
  --duration 15 \
  --max-chunks 10 \
  --smart-crop \
  --output ./my-reels
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

TrendWatch offers **two intelligent cropping methods** to optimize your videos for vertical format:

### MediaPipe (Default) - Face Detection
- **Best for:** Talking heads, interviews, vlogs
- **Speed:** Fast (~95% accuracy)
- **Detects:** Faces using Google's MediaPipe
- **Strategy:** Centers crop on detected faces

```bash
python -m videochunker "VIDEO_INPUT" --crop-method mediapipe
```

### YOLO - Person Detection
- **Best for:** Full-body shots, action, sports
- **Speed:** Moderate (~98% accuracy)
- **Detects:** Full people using YOLOv8
- **Strategy:** Scene-by-scene analysis with smart letterboxing
- **Features:**
  - Detects scene boundaries
  - Tracks people across frames
  - Adds letterboxing when subjects are too wide

```bash
python -m videochunker "VIDEO_INPUT" --crop-method yolo
```

Both methods:
- Fill entire 9:16 screen (no black bars by default)
- Fall back to center crop if nothing detected
- Can be disabled with `--no-smart-crop`

## Platform Specifications

| Platform  | Aspect Ratio | Max Duration | Resolution | Format |
|-----------|--------------|--------------|------------|--------|
| YouTube   | 9:16         | 60s          | 1080x1920  | MP4/H.264 |
| Instagram | 9:16         | 90s          | 1080x1920  | MP4/H.264 |
| Facebook  | 9:16         | 90s          | 1080x1920  | MP4/H.264 |
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
