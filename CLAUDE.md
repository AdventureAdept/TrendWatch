# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CLI tool that processes videos (from URLs or local files) and splits them into 60-second chunks optimized for social media reels (YouTube Shorts, Instagram Reels, Facebook Reels, TikTok). Features smart cropping with MediaPipe face detection that fills the entire 9:16 screen.

See [README.md](README.md) for full usage docs, platform specs, and YouTube upload setup.

## Tech Stack

- Python 3.10+
- FFmpeg (system dependency, called via subprocess)
- OpenCV (opencv-python) for image processing
- Click for CLI

## Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run CLI (default: first 5 chunks, all platforms)
# Input can be a URL or local file path
python3 -m trendwatch <video_input>

# Examples:
# python3 -m trendwatch "https://youtube.com/watch?v=..."
# python3 -m trendwatch "/path/to/video.mp4"
# python3 -m trendwatch "./my-video.mkv"

# Options (long / short alias):
# --platform, -p: Target platform(s) [default: all]
#   Values: youtube/yt, instagram/ig, facebook/fb, tiktok/tk, all
#   Repeatable: -p yt -p ig  OR  comma-separated: -p yt,ig,fb
# --output, -o: Output directory [default: ./output]
# --duration, -d: Chunk duration in seconds [default: 60]
# --max-chunks, -m: Maximum chunks to create [default: 5]
# --smart-crop/--no-smart-crop (--sc/--no-sc): Smart cropping [default: enabled]
# --hflip/--no-hflip (--hf/--no-hf): Horizontal flip [default: enabled]
# --fetch-imdb/--no-fetch-imdb (--imdb/--no-imdb): IMDb metadata [default: enabled]
# --keep-temp (--kt): Keep temporary files
# --upload-youtube/--no-upload-youtube (--u-yt/--no-u-yt): Upload to YouTube [default: disabled]
# --youtube-title (--yt-title): Title template [default: "{filename} - Part {n}"]
# --youtube-description (--yt-desc): Video description [default: ""]
# --youtube-privacy (--yt-priv): Privacy status (public|unlisted|private) [default: public]
# --youtube-category (--yt-cat): Category ID [default: 24 (Entertainment)]
# --youtube-tags (--yt-tags): Comma-separated tags [default: ""]
# --upload-facebook/--no-upload-facebook (--u-fb/--no-u-fb): Upload to Facebook Reels [default: disabled]
# --upload-instagram/--no-upload-instagram (--u-ig/--no-u-ig): Upload to Instagram Reels [default: disabled]
# --meta-title (--mt): Title/caption template [default: "{filename} - Part {n}"]
# --meta-description (--md): Description/caption text [default: ""]
# --meta-tags (--mtags): Comma-separated hashtags [default: ""]
# --meta-privacy (--mp): Facebook privacy (public|friends|only_me) [default: public]
# --upload-only (--uo): Skip processing, upload existing clips from output dir (requires --u-yt, --u-fb, or --u-ig)

# Supported video formats: MP4, MKV, AVI, MOV, WebM, FLV, WMV, M4V

# Run tests
pytest

# Lint
ruff check .
```

## Architecture

```
trendwatch/
├── __main__.py          # CLI entry point
├── downloader.py        # Download video from URL (yt-dlp)
├── chunker.py           # Split video into fixed-duration segments
├── face_detector.py     # Face detection using MediaPipe for smart cropping
├── transcoder.py        # Platform-specific encoding (aspect ratio, bitrate, codec)
├── platforms.py         # Platform specs and presets
├── youtube_uploader.py  # YouTube Data API v3 client with OAuth 2.0
├── meta_uploader.py     # Meta Graph API client for Facebook/Instagram Reels
└── omdb.py              # OMDb API client for IMDb metadata
```

## Key Notes

- YouTube OAuth credentials: `~/.trendwatch/client_secrets.json`
- YouTube token cache: `~/.trendwatch/youtube_token.pickle`
- Credentials .env: `~/.trendwatch/.env` (META_ACCESS_TOKEN, META_PAGE_ID, META_IG_USER_ID, OMDB_API_KEY)
- Meta Graph API: v25.0 — Facebook uploads use auto-fetched Page Access Token (publish_video deprecated)
- Instagram relay: litterbox.catbox.moe (1h expiry) for video_url uploads
- MediaPipe model: `trendwatch/models/face_detection_short_range.tflite`
- Output path: `output/{video_id}/{platform}/`
- Upload results: `output/{video_id}/youtube_uploads.json`, `facebook_uploads.json`, `instagram_uploads.json`

## Platform Encoding

All 4 platforms share identical encoding specs (1080x1920, libx264, aac, 8000k, yuv420p). FFmpeg therefore runs **once** using a canonical platform (youtube if selected, else first platform), and other platform folders are populated by `shutil.copy2` with renamed filenames — no re-encoding.

`PlatformSpec` fields: `name`, `width`, `height`, `video_codec`, `audio_codec`, `video_bitrate`, `audio_bitrate`, `pixel_format`. The fields `max_duration`, `recommended_duration`, and `aspect_ratio` were removed (never read).

