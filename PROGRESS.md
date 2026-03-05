# TrendWatch - Progress Update

**Last Updated:** 2026-03-05 (Session 7)

## Original Goal

Build a CLI tool that downloads videos from YouTube URLs and splits them into 30-second chunks optimized for social media reels (YouTube Shorts, Instagram Reels, Facebook Reels, TikTok), featuring smart face detection for intelligent cropping that fills the entire 9:16 screen.

---

## Core Features - Status

### 1. Download videos from URLs - DONE
- Uses `yt-dlp` to download videos from YouTube (and other supported URLs).
- Handled via `trendwatch/downloader.py`.

### 2. Split video into 30-second chunks - DONE
- FFmpeg-based chunking with configurable duration (`--duration` flag, default 30s).
- Configurable max chunks (`--max-chunks`, default 5).
- Handled via `trendwatch/chunker.py`.

### 3. Smart cropping for intelligent vertical conversion - DONE
- **MediaPipe Face Detection:**
  - ~95%+ accuracy for face detection
  - Handles profiles/angles/occlusions
  - Multi-frame analysis (samples 3 frames at 25%, 50%, 75%)
  - Uses facial keypoints (eye centers) for natural crop centering
  - Confidence-weighted crop calculation
  - Falls back to center crop when no faces detected
  - Best for: Talking heads, interviews, vlogs
  - Handled via `trendwatch/face_detector.py`

### 4. Platform-specific transcoding (9:16, fills screen) - DONE
- All platforms output at 1080x1920 (9:16) MP4/H.264.
- Scale-to-fill with smart crop (no black bars).
- Platform presets defined in `trendwatch/platforms.py`.
- Transcoding handled via `trendwatch/transcoder.py`.

### 5. CLI interface - DONE
- Built with Click.
- Supports all flags: `--platform`, `--output`, `--duration`, `--max-chunks`, `--smart-crop/--no-smart-crop`, `--hflip/--no-hflip`, `--keep-temp`.
- Entry point: `python -m trendwatch <video_input>` (accepts URLs or file paths).

### 6. Multi-platform output - DONE
- YouTube Shorts (9:16, 1080x1920, 60s max)
- Instagram Reels (9:16, 1080x1920, 90s max)
- Facebook Reels (9:16, 1080x1920, **90s max** - updated from 60s)
- TikTok (9:16, 1080x1920, 60s max)
- Can target one or more platforms (`-p yt,ig,fb` or `-p yt -p ig`) or all at once (`-p all`).

### 7. Horizontal flip effect - DONE
- Enabled by default, toggleable with `--hflip/--no-hflip`.

### 8. Local file path support - DONE
- Accept local video files as input (in addition to URLs)
- Auto-detects input type (URL vs file path)
- Skips download step for local files (faster processing)
- Supports: MP4, MKV, AVI, MOV, WebM, FLV, WMV, M4V
- Example: `python -m trendwatch "./video.mp4" -p facebook`

---

## End-to-End Pipeline - VERIFIED WORKING

**Test 1: URL input with MediaPipe (face detection)**
```bash
python3 -m trendwatch https://www.youtube.com/watch?v=gaRI6RMgkV4 -p youtube
```
- Video downloaded from YouTube
- Split into 30s chunks
- MediaPipe face detection (5-6 faces detected per chunk)
- Transcoded to YouTube Shorts format (1080x1920, 9:16)
- Output saved to `./output`

**Test 2: Local file with MediaPipe**
```bash
python3 -m trendwatch ./input/vid.mkv -p facebook
```
- Local file used directly (no download)
- MediaPipe face detection applied
- Transcoded to Facebook Reels format (1080x1920, 9:16)
- Output saved to `./output`

---

## Recent Improvements

### Session 1 (2026-02-08): MediaPipe Upgrade
Replaced OpenCV Haar Cascade with MediaPipe face detection (~60% → ~95% accuracy). Added multi-frame sampling (3 frames), eye-keypoint centering, confidence weighting, and context manager pattern.

### Session 2 (2026-02-14): Local File Support
Added local file input (URL + file path auto-detection). Updated Facebook Reels max duration to 90s.

### Session 3 (2026-03-02): YouTube Upload + IMDb Metadata
Added YouTube Shorts upload via OAuth 2.0, IMDb metadata auto-generation via OMDb API (title, tags, description from `tt#######` filenames), upload-only mode (`--uo`), and short CLI aliases.

### Session 4 (2026-03-02): Meta (Facebook + Instagram) Upload Integration
Built `meta_uploader.py` — Facebook uses `/{page_id}/videos` multipart upload, Instagram uses litterbox.catbox.moe relay → `video_url` parameter. Key lessons: rupload.facebook.com returns 404 for new accounts (don't use it), `ig_user_id` must be the Instagram Business Account ID (not Facebook user ID), and app must be in Live mode.

### Session 5 (2026-03-03): Multi-Platform Selection & Chunk-Based Part Numbers
Added multi-platform `-p` flag (comma-separated or repeated). Upload part numbers now match chunk numbers from filenames instead of sequential index.

---

## Overall Completion

| Feature | Status |
|---------|--------|
| Video downloading (URLs) | Done |
| Local file path support | Done |
| Video chunking | Done |
| Smart cropping - MediaPipe (faces) | Done |
| 9:16 crop that fills screen | Done |
| Platform-specific encoding | Done |
| CLI with all options | Done |
| Multi-platform output | Done |
| Horizontal flip | Done |
| YouTube Shorts upload | Done |
| IMDb metadata auto-generation | Done |
| Facebook Reels upload | Done |
| Instagram Reels upload | Done |
| Upload-only mode | Done |
| Multi-platform `-p` selection | Done |
| Chunk-based part numbers | Done |
| **Overall** | **Complete - all features working** |

---

## Implemented Enhancements

✅ **Local file path support** - Process videos without downloading
✅ **Facebook 90s duration** - Updated to match current platform limits
✅ **YouTube Shorts upload** - OAuth 2.0, auto-refresh token, IMDb metadata
✅ **Facebook Reels upload** - Meta Graph API, multipart upload
✅ **Instagram Reels upload** - Meta Graph API, catbox.moe relay for public URL
✅ **IMDb metadata** - Auto-titles, descriptions, tags from OMDb API
✅ **Upload-only mode** - Re-upload existing clips without reprocessing
✅ **Multi-platform `-p`** - Select multiple platforms: `-p yt,ig,fb` or `-p yt -p ig`
✅ **Chunk-based part numbers** - Part numbers in titles match chunk numbers from filenames
✅ **Transcode-once** - FFmpeg runs once; other platform folders populated by file copy (no re-encoding)
✅ **Meta Graph API v25.0** - Upgraded from v21.0, auto-fetches Page Access Token (publish_video deprecated)
✅ **Instagram litterbox relay** - Switched from catbox.moe (permanent) to litterbox (1h auto-delete)
✅ **AVI codec fix** - Added -analyzeduration/-probesize to chunker and face detector for AVI sources
✅ **Bug fixes** - YouTubeUploader re-instantiation, unbound fb/ig results, Instagram permalink

### Session 5 (2026-03-03): Multi-Platform Selection & Chunk-Based Part Numbers

| What | Detail |
|------|--------|
| Multi-platform `-p` flag | `-p` now accepts multiple values: `-p yt,ig,fb` (comma-separated) or `-p yt -p ig -p fb` (repeated). Default: all |
| Chunk-based part numbers | Upload part numbers now match the chunk number from the filename (e.g., `_chunk_011` → "Part 011") instead of sequential enumeration index |

### Session 6 (2026-03-03): Transcode Once + Remove Dead PlatformSpec Fields

| What | Detail |
|------|--------|
| Transcode-once optimization | FFmpeg now runs once per run instead of once per platform. All 4 platforms share identical specs (1080x1920, libx264, aac, 8000k, yuv420p), so the canonical output is file-copied into each platform folder with renamed filenames — zero re-encoding |
| Removed dead `PlatformSpec` fields | `max_duration`, `recommended_duration`, and `aspect_ratio` were defined in the dataclass and all 4 platform entries but never read anywhere in the codebase — removed entirely |

### Session 7 (2026-03-05): Meta API v25, AVI Fix, Auto-Uploader, Bug Fixes

| What | Detail |
|------|--------|
| Meta Graph API v25.0 | Upgraded from v21.0. `publish_video` permission deprecated — uploader now auto-fetches a Page Access Token from the User token via `/me/accounts` |
| Instagram litterbox relay | Switched from catbox.moe (files stored forever) to litterbox.catbox.moe (1h auto-expiry). Instagram only needs the URL for ~2 min processing |
| AVI frame extraction fix | Added `-analyzeduration 100M -probesize 100M` to both `chunker.py` and `face_detector.py` FFmpeg commands. AVI files with MPEG-4 ASP codec had missing stream dimensions in remuxed MP4 chunks, causing face detection to silently fail |
| Daily auto-uploader | `autopost.py` — uploads pre-processed clips from a flat folder (10/day to YouTube, 25/day to Facebook, 25/day to Instagram). Tracked outside the main repo |
| Instagram permalink fix | `upload_instagram_reel()` now fetches the real `permalink` from the Graph API instead of guessing a URL from the media ID |
| YouTubeUploader re-instantiation bug | Was creating a new `YouTubeUploader()` (triggering OAuth) on every loop iteration — now created once before the loop |
| Unbound `fb_results`/`ig_results` | Variables were uninitialized before conditional branches, causing potential `NameError` — now initialized to `[]` |

## Optional Future Enhancements

- YOLOv8 person detection as alternative smart crop method
- PySceneDetect integration for scene-aware cropping
- Batch processing (multiple videos at once)
- Unit/integration test suite
- Configuration file support (.trendwatch.json)
- Suppress cosmetic MediaPipe/TFLite log warnings
- Progress bars for long operations
- Video quality presets (low/medium/high bitrate)
- ~~Replace catbox.moe relay~~ (done: switched to litterbox with 1h auto-delete)
