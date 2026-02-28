# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CLI tool that processes videos (from URLs or local files) and splits them into 30-second chunks optimized for social media reels (YouTube Shorts, Instagram Reels, Facebook Reels, TikTok). Features smart cropping with MediaPipe (face detection) or YOLO (person detection) that fills the entire 9:16 screen.

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
# --smart-crop/--no-smart-crop: Enable smart cropping with MediaPipe face detection [default: enabled]
# --hflip/--no-hflip: Apply horizontal flip effect to output videos [default: enabled]
# --fetch-imdb/--no-fetch-imdb: Fetch IMDb metadata if filename contains IMDb ID [default: enabled]
# --keep-temp: Keep temporary files

# Supported video formats: MP4, MKV, AVI, MOV, WebM, FLV, WMV, M4V

# IMDb metadata fetching (enabled by default, requires OMDB_API_KEY environment variable):
# export OMDB_API_KEY="your_api_key"
# python -m videochunker "tt0111161.mp4"  # Automatically fetches metadata if IMDb ID detected
# python -m videochunker "tt0111161.mp4" --no-fetch-imdb  # Disable IMDb fetching

# Run tests
pytest

# Lint
ruff check .
```

## YouTube Upload Integration

TrendWatch supports automatic YouTube Shorts upload after video processing using OAuth 2.0 authentication.

### Setup YouTube OAuth Credentials

1. **Create Google Cloud Project:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one

2. **Enable YouTube Data API v3:**
   - Visit [YouTube Data API](https://console.cloud.google.com/apis/library/youtube.googleapis.com)
   - Click "Enable"

3. **Create OAuth 2.0 Credentials:**
   - Go to Credentials → Create Credentials → OAuth client ID
   - Application type: **Desktop app**
   - Download the JSON file

4. **Save Credentials:**
   ```bash
   mkdir -p ~/.trendwatch
   cp ~/Downloads/client_secret_*.json ~/.trendwatch/client_secrets.json
   ```

5. **First-time Authorization:**
   - Run any command with `--upload-youtube`
   - Browser will open for authorization
   - Token will be cached at `~/.trendwatch/youtube_token.pickle`
   - Future runs will use cached token (no browser needed)

### YouTube Upload Options

```bash
# --upload-youtube/--no-upload-youtube: Enable YouTube upload [default: disabled]
# --youtube-title: Title template with placeholders [default: "{filename} - Part {n}"]
#   Placeholders: {n} (chunk number), {filename} (base name), {total} (total videos)
# --youtube-description: Video description [default: ""]
#   Note: #Shorts tag is auto-added to description
# --youtube-privacy: Privacy status (public|unlisted|private) [default: public]
# --youtube-tags: Comma-separated tags [default: ""]
```

### YouTube Upload Examples

```bash
# Basic upload (process + upload to YouTube)
python -m videochunker "video.mp4" --upload-youtube

# Upload with IMDb metadata (automatic title/description/tags)
python -m videochunker "tt1856101.mp4" --upload-youtube
# Auto-generates: "Blade Runner 2049 (2017) - Part 1"
# Description: Plot summary + IMDb rating + Director
# Tags: Genre + Actors + Year + "Shorts"

# Custom metadata (overrides IMDb)
python -m videochunker "tt1856101.mp4" \
  --platform youtube \
  --upload-youtube \
  --youtube-title "{filename} - Epic Scene #{n}" \
  --youtube-description "Amazing moment from Blade Runner 2049" \
  --youtube-tags "movie,scifi,shorts,cinema"

# Unlisted uploads for review
python -m videochunker "video.mp4" \
  --upload-youtube \
  --youtube-privacy unlisted

# Multi-platform processing (uploads only YouTube Shorts)
python -m videochunker "video.mp4" \
  --platform all \
  --upload-youtube
# Processes for all platforms, but only uploads YouTube Shorts
```

### IMDb Metadata Integration

When a video filename contains an IMDb ID (e.g., `tt1856101.mp4`):

1. **Metadata is fetched** from OMDb API
2. **YouTube uploads automatically use** the metadata:
   - **Title:** `Movie Title (Year) - Part N`
   - **Description:** Plot summary + IMDb rating + Director
   - **Tags:** Genres + Actors + Year + "Shorts" + "MovieClips"

**Override behavior:**
- Providing `--youtube-title` overrides auto-generated titles
- Providing `--youtube-description` overrides IMDb plot
- Providing `--youtube-tags` adds to (not replaces) IMDb tags

### Upload Metadata

Upload results are saved to `{output_dir}/youtube_uploads.json`:

```json
{
  "uploaded_at": "2026-02-15T21:30:00.123456",
  "total_uploads": 3,
  "videos": [
    {
      "video_id": "dQw4w9WgXcQ",
      "video_url": "https://youtube.com/shorts/dQw4w9WgXcQ",
      "title": "Blade Runner - Part 001",
      "privacy_status": "public",
      "uploaded_at": "2026-02-15T21:30:15.123456",
      "file_path": ".../youtube_shorts/video_chunk_001_youtube_shorts.mp4"
    }
  ]
}
```

### YouTube API Quotas

- **Daily quota:** 10,000 units (default)
- **Upload cost:** ~1,600 units per video
- **Max uploads/day:** ~6 videos
- **Reset time:** Midnight Pacific Time
- **Quota increase:** Available via [Google Cloud Console](https://console.cloud.google.com/iam-admin/quotas)

### Troubleshooting

**Missing credentials:**
- Error will show setup instructions
- Ensure `~/.trendwatch/client_secrets.json` exists
- Processing continues even if upload fails

**Quota exceeded:**
- Clear error message with daily limits
- Partial uploads are saved to JSON
- Request quota increase if needed

**Token expired:**
- Token auto-refreshes using refresh_token
- Re-authorization required if refresh fails


## Architecture

```
videochunker/
├── __main__.py          # CLI entry point
├── downloader.py        # Download video from URL (yt-dlp)
├── chunker.py           # Split video into fixed-duration segments
├── face_detector.py     # Face detection using MediaPipe for smart cropping
├── transcoder.py        # Platform-specific encoding (aspect ratio, bitrate, codec)
├── platforms.py         # Platform specs and presets
├── youtube_uploader.py  # YouTube Data API v3 client with OAuth 2.0
└── omdb.py              # OMDb API client for IMDb metadata
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
- `opencv-python`: OpenCV for image processing
- `mediapipe`: Face detection for smart cropping
- `click`: CLI framework
- `requests`: HTTP client for TikTok API calls
- `google-api-python-client`: YouTube Data API v3 client
- `google-auth-oauthlib`: OAuth 2.0 authentication for YouTube uploads
- FFmpeg must be installed system-wide (`apt install ffmpeg` or `brew install ffmpeg`)
