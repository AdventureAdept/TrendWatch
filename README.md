# TrendWatch

CLI tool that processes videos (from URLs or local files) and splits them into 60-second chunks optimized for social media reels (YouTube Shorts, Instagram Reels, Facebook Reels, TikTok).

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Output Structure](#output-structure)
- [YouTube Upload Integration](#youtube-upload-integration)
  - [Quick Start](#quick-start)
  - [Upload Examples](#upload-examples)
  - [Upload Options](#upload-options)
  - [API Quotas](#api-quotas)
  - [Upload Metadata](#upload-metadata)
- [Meta Upload Integration](#meta-upload-integration)
  - [Meta Quick Start](#meta-quick-start)
  - [Meta Upload Examples](#meta-upload-examples)
  - [Meta Upload Options](#meta-upload-options)
- [IMDb Metadata](#imdb-metadata)
- [Smart Cropping](#smart-cropping)
- [Platform Specifications](#platform-specifications)
- [Development](#development)
- [License](#license)

## Features

- 📥 Download videos from any URL (YouTube, Twitter, etc.) using yt-dlp
- 📁 Process local video files directly (no download needed)
- ✂️ Split videos into 60-second chunks (configurable)
- 🎨 Transcode to platform-specific formats (9:16 aspect ratio, proper encoding) — **FFmpeg runs once** regardless of how many platforms are selected; other platform folders are populated by file copy
- 🤖 Smart cropping with **MediaPipe face detection**
- 🎬 **IMDb metadata auto-generation** — fetches title, plot, cast, rating, and genres from OMDb API when the filename contains an IMDb ID (`tt#######`)
- 📱 Support for YouTube, Instagram, Facebook, and TikTok
- 📤 **Automated YouTube Shorts upload** with OAuth 2.0 authentication
- 📘 **Automated Facebook Reels upload** via Meta Graph API
- 📷 **Automated Instagram Reels upload** via Meta Graph API

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
python3 -m trendwatch "https://youtube.com/watch?v=..."
```

**From local file:**
```bash
python3 -m trendwatch "/path/to/video.mp4"
python3 -m trendwatch "./my-video.mkv"
```

**Supported video formats:** MP4, MKV, AVI, MOV, WebM, FLV, WMV, M4V

### Specify platform(s):
```bash
# Single platform
python3 -m trendwatch "https://youtube.com/watch?v=..." --platform youtube
python3 -m trendwatch "https://youtube.com/watch?v=..." -p yt

# Multiple platforms (comma-separated)
python3 -m trendwatch "/home/user/video.mp4" -p yt,ig,fb

# Multiple platforms (repeated flag)
python3 -m trendwatch "./video.mkv" -p yt -p ig -p fb
```

### Custom output directory:
```bash
python3 -m trendwatch "VIDEO_INPUT" -o ./my-reels
```

### Custom chunk duration:
```bash
python3 -m trendwatch "VIDEO_INPUT" -d 60
```

### Limit number of chunks (default is 5):
```bash
python3 -m trendwatch "VIDEO_INPUT" -m 10
```

### Disable smart cropping (use center crop):
```bash
python3 -m trendwatch "VIDEO_INPUT" --no-sc
```

### Keep temporary files (raw chunks):
```bash
python3 -m trendwatch "VIDEO_INPUT" --kt
```

### Complete example with all options:
```bash
python3 -m trendwatch "/movies/inception.mp4" \
  -p yt,ig,fb -d 15 -m 10 --sc -o ./my-reels
```

### CLI Quick Reference

| Option | Long Form | Short |
|--------|-----------|-------|
| Platform | `--platform` | `-p` (values: `yt`, `ig`, `fb`, `tk`, `all` — repeatable/comma-separated) |
| Output dir | `--output` | `-o` |
| Duration | `--duration` | `-d` |
| Max chunks | `--max-chunks` | `-m` |
| Smart crop | `--smart-crop / --no-smart-crop` | `--sc / --no-sc` |
| Flip | `--hflip / --no-hflip` | `--hf / --no-hf` |
| Keep temp | `--keep-temp` (keeps `chunks/` dir) | `--kt` |
| IMDb fetch | `--fetch-imdb / --no-fetch-imdb` | `--imdb / --no-imdb` |
| Upload YT | `--upload-youtube / --no-upload-youtube` | `--u-yt / --no-u-yt` |
| YT title | `--youtube-title` | `--yt-title` |
| YT desc | `--youtube-description` | `--yt-desc` |
| YT privacy | `--youtube-privacy` | `--yt-priv` |
| YT category | `--youtube-category` | `--yt-cat` |
| YT tags | `--youtube-tags` | `--yt-tags` |
| Upload FB | `--upload-facebook / --no-upload-facebook` | `--u-fb / --no-u-fb` |
| Upload IG | `--upload-instagram / --no-upload-instagram` | `--u-ig / --no-u-ig` |
| Meta title | `--meta-title` | `--mt` |
| Meta desc | `--meta-description` | `--md` |
| Meta tags | `--meta-tags` | `--mtags` |
| Meta privacy | `--meta-privacy` | `--mp` |
| Upload only | `--upload-only` | `--uo` |

## Output Structure

The top-level folder name (`{video_id}`) is chosen automatically:
1. IMDb ID from the filename (e.g. `tt1856101`)
2. YouTube video ID from the URL (e.g. `dQw4w9WgXcQ`)
3. Input filename stem as a fallback

```
output/
└── {video_id}/
    ├── chunks/                              (deleted after processing unless --kt)
    │   ├── {stem}_chunk_001.mp4
    │   └── ...
    ├── youtube_shorts/
    │   ├── {stem}_chunk_001_youtube_shorts.mp4
    │   ├── {stem}_chunk_002_youtube_shorts.mp4
    │   └── ...
    ├── instagram_reels/
    │   ├── {stem}_chunk_001_instagram_reels.mp4
    │   └── ...
    ├── facebook_reels/
    │   └── ...
    ├── tiktok/
    │   └── ...
    ├── {video_id}_metadata.json    (if IMDb ID found in filename)
    ├── youtube_uploads.json        (if --u-yt used)
    ├── facebook_uploads.json       (if --u-fb used)
    └── instagram_uploads.json      (if --u-ig used)
```

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
   python3 -m trendwatch "video.mp4" --u-yt
   ```
   - First run: Browser opens for authorization
   - Token cached at `~/.trendwatch/youtube_token.pickle`
   - Future runs: No browser needed (token auto-refreshes)

### Upload Examples

**Basic upload:**
```bash
python3 -m trendwatch "video.mp4" --u-yt
```

**Upload with IMDb metadata (automatic):**
```bash
# Video with IMDb ID in filename
python3 -m trendwatch "tt1856101.mp4" --u-yt

# Automatically generates:
# Title: "Blade Runner 2049 (2017) - Part 1"
# Description: Plot + IMDb rating + Director
# Tags: SciFi, Action, Drama, HarrisonFord, RyanGosling, 2017, Shorts, MovieClips
```

**Custom titles and metadata (overrides IMDb):**
```bash
python3 -m trendwatch "tt1856101.mp4" \
  --u-yt \
  --yt-title "Epic Scene #{n} - {filename}" \
  --yt-desc "Amazing cinematic moments" \
  --yt-tags "movie,shorts,cinema"
```

**Unlisted uploads (for review):**
```bash
python3 -m trendwatch "video.mp4" --u-yt --yt-priv unlisted
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
| `--upload-only` | `--uo` | Skip processing, upload existing clips (works with `--u-yt`, `--u-fb`, `--u-ig`) | Disabled | - |

**Metadata priority** (highest wins):
1. IMDb metadata (if filename contains `tt#######`) — auto-generates title, description, tags from movie data
2. YouTube source metadata (if input was a YouTube URL) — uses source video title, description, and tags
3. CLI `--yt-*` options — used exactly as provided

CLI options always override IMDb/source metadata when explicitly set.

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


## Meta Upload Integration

TrendWatch can automatically upload your processed videos to Facebook Reels and Instagram Reels after transcoding using the Meta Graph API v25.0.

### Meta Quick Start

1. **Create a Meta app** (one-time setup):
   - Go to [Meta for Developers](https://developers.facebook.com)
   - Create an app → add **Facebook Login** and **Instagram Graph API** products
   - Switch the app to **Live mode** (required for uploads to work)

2. **Generate a User Access Token** with these scopes:
   - `pages_manage_posts`
   - `pages_show_list`
   - `pages_read_engagement`
   - `instagram_basic`
   - `instagram_content_publish`

   Use [Graph API Explorer](https://developers.facebook.com/tools/explorer/) (v25.0) to generate the token. The `publish_video` scope is no longer needed — TrendWatch automatically fetches a Page Access Token from your User token for Facebook video uploads.

3. **Get your Page ID and Instagram Business Account ID:**
   - Run `GET /me/accounts` in Graph Explorer to get your `page_id` and the page's access token
   - Run `GET /{page_id}?fields=instagram_business_account` to get your `ig_user_id`

4. **Save credentials** to `~/.trendwatch/.env`:
   ```bash
   mkdir -p ~/.trendwatch
   cat >> ~/.trendwatch/.env << 'EOF'
   META_ACCESS_TOKEN=YOUR_LONG_LIVED_TOKEN
   META_PAGE_ID=YOUR_PAGE_ID
   META_IG_USER_ID=YOUR_IG_USER_ID
   EOF
   ```

   You can also add your OMDb API key to the same file:
   ```bash
   echo 'OMDB_API_KEY=your_key' >> ~/.trendwatch/.env
   ```

5. **Upload videos:**
   ```bash
   # Facebook only
   python3 -m trendwatch "video.mp4" -p fb --u-fb

   # Instagram only
   python3 -m trendwatch "video.mp4" -p ig --u-ig

   # Both at once
   python3 -m trendwatch "video.mp4" --u-fb --u-ig
   ```

> **Note:** Long-lived tokens expire after 60 days but are auto-extended each time they're used. Instagram Reels are always public (no privacy setting).

### Meta Upload Examples

**Facebook Reel with IMDb metadata (automatic):**
```bash
python3 -m trendwatch "tt1856101.mp4" -p fb --u-fb
# Auto-generates title, description, and hashtags from IMDb data
```

**Instagram Reel with custom caption:**
```bash
python3 -m trendwatch "video.mp4" -p ig --u-ig \
  --mt "Epic Scene #{n}" \
  --md "Amazing cinematic moments" \
  --mtags "movie,shorts,cinema"
```

**Upload to both platforms with friends-only Facebook privacy:**
```bash
python3 -m trendwatch "video.mp4" -m 1 --u-fb --u-ig --mp friends
```

**Upload-only from existing folder:**
```bash
python3 -m trendwatch "output/Voz2OVsKbQY" --uo --u-fb --u-ig
```

### Meta Upload Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--upload-facebook` | `--u-fb` | Enable Facebook Reels upload | Disabled |
| `--upload-instagram` | `--u-ig` | Enable Instagram Reels upload | Disabled |
| `--meta-title` | `--mt` | Title/caption template (`{n}`, `{filename}`, `{total}`) | `{filename} - Part {n}` |
| `--meta-description` | `--md` | Description / caption text | Empty |
| `--meta-tags` | `--mtags` | Comma-separated hashtags (without `#`) | Empty |
| `--meta-privacy` | `--mp` | Facebook privacy (`public`/`friends`/`only_me`) | `public` |

**Metadata priority** (same as YouTube):
1. IMDb metadata (if filename contains `tt#######`) — auto-generates titles, descriptions, hashtags
2. YouTube source metadata (if downloaded from YouTube) — uses source title and tags
3. CLI `--meta-*` options — used as provided

Upload results are saved to:
- `{output_dir}/facebook_uploads.json`
- `{output_dir}/instagram_uploads.json`


## IMDb Metadata

When the input filename contains an IMDb ID (`tt` followed by 7–8 digits), TrendWatch automatically fetches movie/show metadata from the OMDb API and uses it to generate upload titles, descriptions, and tags for YouTube, Facebook, and Instagram — no manual metadata entry needed.

**Data fetched:** Title, Year, Plot (full), Director, Actors, Genre, IMDb Rating, Runtime, Type (movie/series)

**Saved to:** `output/{video_id}/{video_id}_metadata.json`

### Setup

1. Get a free API key from http://www.omdbapi.com/apikey.aspx
2. Add to `~/.trendwatch/.env`:
   ```
   OMDB_API_KEY=your_key_here
   ```
   (This is the same `.env` file used for Meta credentials)

### Usage

- Enabled by default — just name your file with the IMDb ID: `tt1856101.mkv`
- The ID can appear anywhere in the name: `movie_tt1856101_1080p.mp4` also works
- Disable with `--no-imdb` if not needed
- Silently skipped if `OMDB_API_KEY` is not set

### Example

```bash
python3 -m trendwatch "tt1856101.mkv" --u-yt --u-fb --u-ig
# Automatically generates for all upload platforms:
# Title:       "Blade Runner 2049 (2017) - Part 001"
# Description: Full plot + IMDb rating + director
# Tags/hashtags: genres, lead actors, year
```

### Options

| Option | Short | Default |
|--------|-------|---------|
| `--fetch-imdb / --no-fetch-imdb` | `--imdb / --no-imdb` | Enabled (skips silently if no API key) |


## Smart Cropping

TrendWatch uses a two-stage smart cropping pipeline to intelligently crop videos for vertical format:

1. **MediaPipe** (primary): Google's face detection — centers crop on detected faces using eye position for stability
2. **Center crop** (fallback): Used when MediaPipe doesn't detect a face

- **Best for:** Talking heads, interviews, vlogs
- **Speed:** Fast with high accuracy

```bash
# Smart cropping is enabled by default
python3 -m trendwatch "VIDEO_INPUT"

# Disable smart cropping (use center crop only)
python3 -m trendwatch "VIDEO_INPUT" --no-smart-crop
```

Features:
- Samples multiple frames across the video for consistent framing
- Uses eye centers for more stable positioning than bounding boxes
- Weights detections by confidence score
- Fills entire 9:16 screen (no black bars)

## Platform Specifications

All platforms share identical encoding settings (1080x1920, H.264, AAC, 8 Mbps). FFmpeg runs once and the output is copied into each selected platform's folder.

| Platform  | Aspect Ratio | Max Duration | Resolution | Auto-Upload |
|-----------|--------------|--------------|------------|-------------|
| YouTube   | 9:16         | 3 min        | 1080x1920  | ✅ `--u-yt` |
| Instagram | 9:16         | 90s          | 1080x1920  | ✅ `--u-ig` |
| Facebook  | 9:16         | 90s          | 1080x1920  | ✅ `--u-fb` |
| TikTok    | 9:16         | 10 min       | 1080x1920  | — |

## Development

This project was developed with [Claude Code](https://claude.ai/code), Anthropic's AI-powered coding assistant. Claude was instrumental in:
- Architecture design and planning
- Implementation of all core modules
- Face detection integration
- CLI interface development
- Testing and refinement

## License

MIT
