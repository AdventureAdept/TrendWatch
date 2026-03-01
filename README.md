# Video Chunker

CLI tool that processes videos (from URLs or local files) and splits them into 60-second chunks optimized for social media reels (YouTube Shorts, Instagram Reels, Facebook Reels, TikTok).

## Table of Contents

- [Features](#features)
- [YouTube Upload Integration](#youtube-upload-integration)
  - [Quick Start](#quick-start)
  - [Upload Examples](#upload-examples)
  - [Upload Options](#upload-options)
  - [API Quotas](#api-quotas)
  - [Upload Metadata](#upload-metadata)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Output Structure](#output-structure)
- [Smart Cropping](#smart-cropping)
- [Platform Specifications](#platform-specifications)
- [Development](#development)
- [License](#license)

## Features

- 📥 Download videos from any URL (YouTube, Twitter, etc.) using yt-dlp
- 📁 Process local video files directly (no download needed)
- ✂️ Split videos into 60-second chunks (configurable)
- 🎨 Transcode to platform-specific formats (9:16 aspect ratio, proper encoding)
- 🤖 Smart cropping with **MediaPipe face detection** and **YOLOv8 person detection**
- 📱 Support for YouTube, Instagram, Facebook, and TikTok
- 📤 **Automated YouTube Shorts upload** with OAuth 2.0 authentication

## YouTube Upload Integration

TrendWatch can automatically upload your processed videos to YouTube Shorts after transcoding.

### Quick Start

1. **Get YouTube API credentials** (one-time setup):
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a project and enable [YouTube Data API v3](https://console.cloud.google.com/apis/library/youtube.googleapis.com)
   - Create OAuth 2.0 credentials (Desktop app)
   - Download `client_secrets.json`

2. **Save credentials:**
   ```bash
   mkdir -p ~/.trendwatch
   cp ~/Downloads/client_secret_*.json ~/.trendwatch/client_secrets.json
   ```

3. **Upload videos:**
   ```bash
   python -m videochunker "video.mp4" --u-yt
   ```
   - First run: Browser opens for authorization
   - Token cached at `~/.trendwatch/youtube_token.pickle`
   - Future runs: No browser needed (token auto-refreshes)

### Upload Examples

**Basic upload:**
```bash
python -m videochunker "video.mp4" --u-yt
```

**Upload with IMDb metadata (automatic):**
```bash
# Video with IMDb ID in filename
python -m videochunker "tt1856101.mp4" --u-yt

# Automatically generates:
# Title: "Blade Runner 2049 (2017) - Part 1"
# Description: Plot + IMDb rating + Director
# Tags: SciFi, Action, Drama, HarrisonFord, RyanGosling, 2017, Shorts, MovieClips
```

**Custom titles and metadata (overrides IMDb):**
```bash
python -m videochunker "tt1856101.mp4" \
  --u-yt \
  --yt-title "Epic Scene #{n} - {filename}" \
  --yt-desc "Amazing cinematic moments" \
  --yt-tags "movie,shorts,cinema"
```

**Unlisted uploads (for review):**
```bash
python -m videochunker "video.mp4" --u-yt --yt-priv unlisted
```

### Upload Options

| Option | Short | Description | Default | IMDb Auto-Fill |
|--------|-------|-------------|---------|----------------|
| `--upload-youtube` | `--u-yt` | Enable YouTube upload | Disabled | - |
| `--youtube-title` | `--yt-title` | Title template (`{n}`, `{filename}`, `{total}`) | `{filename} - Part {n}` | `Title (Year) - Part N` |
| `--youtube-description` | `--yt-desc` | Video description (auto-adds #Shorts) | Empty | Plot + Rating + Director |
| `--youtube-privacy` | `--yt-priv` | Privacy (public/unlisted/private) | `public` | - |
| `--youtube-category` | `--yt-cat` | Category ID | `24` (Entertainment) | - |
| `--youtube-tags` | `--yt-tags` | Comma-separated tags | Empty | Genre + Actors + Year |
| `--upload-only` | `--uo` | Skip processing, upload existing clips (requires `--u-yt`) | Disabled | - |

**Note:** When IMDb metadata is available (filename contains `tt#######`), titles, descriptions, and tags are automatically generated from movie data. CLI options override these defaults.

### API Quotas

- **Daily limit:** 10,000 units (~6 uploads)
- **Upload cost:** ~1,600 units per video
- **Reset time:** Midnight Pacific Time
- [Request quota increase](https://console.cloud.google.com/iam-admin/quotas)

### Upload Metadata

Results are saved to `{output_dir}/youtube_uploads.json`:

```json
{
  "uploaded_at": "2026-02-15T21:30:00",
  "total_uploads": 3,
  "videos": [
    {
      "video_id": "dQw4w9WgXcQ",
      "video_url": "https://youtube.com/shorts/dQw4w9WgXcQ",
      "title": "Epic Scene #001 - movie",
      "privacy_status": "public",
      "uploaded_at": "2026-02-15T21:30:15",
      "file_path": "./output/video/youtube_shorts/chunk_001.mp4"
    }
  ]
}
```


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
git clone https://github.com/AdventureAdept/TrendWatch.git
cd TrendWatch

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
# Long form
python -m videochunker "https://youtube.com/watch?v=..." --platform youtube

# Short form (yt, ig, fb, tk)
python -m videochunker "https://youtube.com/watch?v=..." -p yt
python -m videochunker "/home/user/video.mp4" -p ig
python -m videochunker "./video.mkv" -p fb
```

### Custom output directory:
```bash
python -m videochunker "VIDEO_INPUT" -o ./my-reels
```

### Custom chunk duration:
```bash
python -m videochunker "VIDEO_INPUT" -d 60
```

### Limit number of chunks (default is 5):
```bash
python -m videochunker "VIDEO_INPUT" -m 10
```

### Disable smart cropping (use center crop):
```bash
python -m videochunker "VIDEO_INPUT" --no-sc
```

### Keep temporary files:
```bash
python -m videochunker "VIDEO_INPUT" --kt
```

### Complete example with all options:
```bash
python -m videochunker "/movies/inception.mp4" \
  -p tk -d 15 -m 10 --sc -o ./my-reels
```

### CLI Quick Reference

| Option | Long Form | Short |
|--------|-----------|-------|
| Platform | `--platform` | `-p` (values: `yt`, `ig`, `fb`, `tk`, `all`) |
| Output dir | `--output` | `-o` |
| Duration | `--duration` | `-d` |
| Max chunks | `--max-chunks` | `-m` |
| Smart crop | `--smart-crop / --no-smart-crop` | `--sc / --no-sc` |
| Flip | `--hflip / --no-hflip` | `--hf / --no-hf` |
| Keep temp | `--keep-temp` | `--kt` |
| IMDb fetch | `--fetch-imdb / --no-fetch-imdb` | `--imdb / --no-imdb` |
| Upload YT | `--upload-youtube / --no-upload-youtube` | `--u-yt / --no-u-yt` |
| YT title | `--youtube-title` | `--yt-title` |
| YT desc | `--youtube-description` | `--yt-desc` |
| YT privacy | `--youtube-privacy` | `--yt-priv` |
| YT category | `--youtube-category` | `--yt-cat` |
| YT tags | `--youtube-tags` | `--yt-tags` |

## Output Structure

```
output/
└── {video_id}/
    ├── youtube_shorts/
    │   ├── video_chunk_001_youtube_shorts.mp4
    │   ├── video_chunk_002_youtube_shorts.mp4
    │   └── ...
    ├── instagram_reels/
    │   ├── video_chunk_001_instagram_reels.mp4
    │   └── ...
    ├── facebook_reels/
    │   └── ...
    ├── tiktok/
    │   └── ...
    └── youtube_uploads.json  (if --u-yt used)
```

## Smart Cropping

TrendWatch uses a three-stage smart cropping pipeline to intelligently crop videos for vertical format:

1. **MediaPipe** (primary): Google's face detection — centers crop on detected faces using eye position for stability
2. **YOLOv8** (fallback): Person detection when no faces are found — crops to detected person bounding box
3. **Center crop** (final fallback): Used when neither MediaPipe nor YOLO detect a subject

- **Best for:** Talking heads, interviews, vlogs, action clips with people
- **Speed:** Fast with high accuracy

```bash
# Smart cropping is enabled by default
python -m videochunker "VIDEO_INPUT"

# Disable smart cropping (use center crop only)
python -m videochunker "VIDEO_INPUT" --no-smart-crop
```

Features:
- Samples multiple frames across the video for consistent framing
- Uses eye centers for more stable positioning than bounding boxes
- Weights detections by confidence score
- Fills entire 9:16 screen (no black bars)

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
