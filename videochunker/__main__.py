"""CLI entry point for videochunker."""

import json
import logging
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import click

from .chunker import VideoChunker
from .downloader import VideoDownloader
from .omdb import OMDbClient
from .platforms import PlatformType, get_all_platforms, get_platform_spec
from .transcoder import VideoTranscoder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)


def extract_youtube_id(url: str) -> str | None:
    """Extract YouTube video ID from URL.

    Args:
        url: YouTube URL

    Returns:
        Video ID or None if not found

    Examples:
        https://youtube.com/watch?v=dQw4w9WgXcQ -> dQw4w9WgXcQ
        https://youtu.be/dQw4w9WgXcQ -> dQw4w9WgXcQ
    """
    # Parse URL
    parsed = urlparse(url)

    # youtube.com/watch?v=VIDEO_ID
    if 'youtube.com' in parsed.netloc:
        query_params = parse_qs(parsed.query)
        if 'v' in query_params:
            return query_params['v'][0]

    # youtu.be/VIDEO_ID
    if 'youtu.be' in parsed.netloc:
        return parsed.path.lstrip('/')

    return None


def extract_imdb_id(filename: str) -> str | None:
    """Extract IMDb ID from filename.

    Args:
        filename: Video filename

    Returns:
        IMDb ID (e.g., tt1234567) or None
    """
    match = re.search(r'(tt\d{7,8})', filename)
    return match.group(1) if match else None


def detect_input_type(video_input: str) -> tuple[str, Path | None]:
    """Detect if input is URL or local file path.

    Args:
        video_input: Either a URL or file path

    Returns:
        Tuple of (input_type, video_path)
        - input_type: "url" or "file"
        - video_path: Path to video file (None for URLs, actual path for files)

    Raises:
        FileNotFoundError: If local file doesn't exist
        ValueError: If path is not a file or has unsupported format
    """
    if video_input.startswith(('http://', 'https://', 'www.')):
        # URL mode - download required
        return "url", None
    else:
        # Local file mode - verify exists
        path = Path(video_input).resolve()

        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {video_input}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {video_input}")

        # Verify it's a video file (check extension)
        valid_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv', '.m4v'}
        if path.suffix.lower() not in valid_extensions:
            raise ValueError(f"Unsupported file format: {path.suffix}")

        return "file", path


@click.command()
@click.argument("video_input")
@click.option(
    "--platform",
    "-p",
    type=click.Choice(["youtube", "instagram", "facebook", "tiktok", "all"]),
    default="all",
    help="Target platform for output videos",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="./output",
    help="Output directory for processed videos",
)
@click.option(
    "--duration",
    "-d",
    type=int,
    default=60,
    help="Chunk duration in seconds (recommended: 60-90s for optimal engagement)",
)
@click.option(
    "--max-chunks",
    "-m",
    type=int,
    default=5,
    help="Maximum number of chunks to create (default: 5)",
)
@click.option(
    "--smart-crop/--no-smart-crop",
    default=True,
    help="Enable smart cropping with MediaPipe face detection (default: enabled)",
)
@click.option(
    "--hflip/--no-hflip",
    default=True,
    help="Apply horizontal flip effect to output videos (default: enabled)",
)
@click.option(
    "--keep-temp",
    is_flag=True,
    help="Keep temporary files after processing",
)
@click.option(
    "--fetch-imdb/--no-fetch-imdb",
    default=True,
    help="Fetch IMDb metadata if filename contains IMDb ID (default: enabled, requires OMDB_API_KEY env var)",
)
@click.option(
    "--upload-youtube/--no-upload-youtube",
    default=False,
    help="Upload processed videos to YouTube after transcoding (requires OAuth setup)",
)
@click.option(
    "--youtube-title",
    default="{filename} - Part {n}",
    help="Title template for YouTube uploads. Placeholders: {n}, {filename}, {total}",
)
@click.option(
    "--youtube-description",
    default="",
    help="Description for YouTube uploads (auto-adds #Shorts tag)",
)
@click.option(
    "--youtube-privacy",
    type=click.Choice(["public", "unlisted", "private"]),
    default="public",
    help="Privacy status for YouTube uploads",
)
@click.option(
    "--youtube-tags",
    default="",
    help="Comma-separated tags for YouTube uploads",
)
def main(
    video_input: str,
    platform: PlatformType,
    output: str,
    duration: int,
    max_chunks: int,
    smart_crop: bool,
    hflip: bool,
    keep_temp: bool,
    fetch_imdb: bool,
    upload_youtube: bool,
    youtube_title: str,
    youtube_description: str,
    youtube_privacy: str,
    youtube_tags: str,
):
    """Split videos from URLs or local files into platform-specific reels.

    VIDEO_INPUT can be:
      - YouTube URL: https://youtube.com/watch?v=...
      - Local file path: /path/to/video.mp4 or ./video.mkv
    """
    # Detect input type
    try:
        input_type, local_path = detect_input_type(video_input)
    except (FileNotFoundError, ValueError) as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()

    click.echo(f"🎬 Video Chunker - Processing: {video_input}")
    click.echo(f"📱 Target platform(s): {platform}")
    click.echo(f"⏱️  Chunk duration: {duration}s")
    click.echo(f"📊 Max chunks: {max_chunks}")
    if smart_crop:
        click.echo(f"🤖 Smart crop: enabled (MediaPipe)")
    else:
        click.echo(f"🤖 Smart crop: disabled")
    click.echo(f"🔄 Horizontal flip: {'enabled' if hflip else 'disabled'}\n")

    # Check FFmpeg availability
    if not shutil.which("ffmpeg"):
        click.echo("❌ Error: FFmpeg is not installed or not in PATH", err=True)
        click.echo("Install FFmpeg: https://ffmpeg.org/download.html", err=True)
        sys.exit(1)

    base_output_dir = Path(output)
    downloader = VideoDownloader()
    transcoder = VideoTranscoder(smart_crop=smart_crop, hflip=hflip)

    try:
        # Step 1: Handle input (download URL or use local file)
        if input_type == "url":
            # URL mode - download video
            click.echo("📥 Downloading video...")
            video_path, yt_source_metadata = downloader.download(video_input)
            click.echo(f"✅ Downloaded: {video_path.name}\n")
        else:
            # Local file mode - use directly
            click.echo(f"📁 Using local file: {local_path.name}")
            video_path = local_path
            yt_source_metadata = None
            click.echo()

        # Determine video-specific output folder
        folder_name = None

        # Priority 1: IMDb ID from filename
        imdb_id = extract_imdb_id(video_path.name)
        if imdb_id:
            folder_name = imdb_id
            click.echo(f"📂 Output folder: {folder_name}/ (IMDb ID)")

        # Priority 2: YouTube video ID from URL
        if not folder_name and input_type == "url":
            yt_id = extract_youtube_id(video_input)
            if yt_id:
                folder_name = yt_id
                click.echo(f"📂 Output folder: {folder_name}/ (YouTube ID)")

        # Priority 3: Fallback to filename
        if not folder_name:
            folder_name = video_path.stem
            click.echo(f"📂 Output folder: {folder_name}/ (filename)")

        # Create video-specific output directory
        output_dir = base_output_dir / folder_name
        output_dir.mkdir(parents=True, exist_ok=True)
        click.echo()

        # Step 2: Fetch IMDb metadata (optional, enabled by default)
        if fetch_imdb:
            # Check if filename contains IMDb ID
            imdb_id = extract_imdb_id(video_path.name)
            if imdb_id:
                click.echo(f"🔍 Detected IMDb ID: {imdb_id}")
                try:
                    omdb_client = OMDbClient()
                    click.echo(f"📡 Fetching metadata from OMDb API...")
                    metadata_path = omdb_client.fetch_and_save(video_path, output_dir)
                    if metadata_path:
                        click.echo(f"✅ Saved metadata: {metadata_path.name}\n")
                except ValueError as e:
                    # No API key - show helpful message
                    if "API key required" in str(e):
                        click.echo(f"⚠️  Skipping IMDb fetch: No API key set")
                        click.echo(f"   Get free key: http://www.omdbapi.com/apikey.aspx")
                        click.echo(f"   Then run: export OMDB_API_KEY='your_key'\n")
                    else:
                        click.echo(f"⚠️  IMDb fetch failed: {e}\n")
                except Exception as e:
                    # Network or API failure - show error but continue
                    click.echo(f"⚠️  IMDb fetch failed: {e}\n")

        # Step 3: Chunk video
        chunks_dir = output_dir / "chunks"
        click.echo(f"✂️  Splitting into {duration}s chunks (max: {max_chunks})...")
        chunker = VideoChunker(chunk_duration=duration, max_chunks=max_chunks)
        chunk_paths = chunker.chunk(video_path, chunks_dir)
        click.echo(f"✅ Created {len(chunk_paths)} chunks\n")

        # Step 4: Transcode for platforms
        platforms = get_all_platforms() if platform == "all" else [platform]

        for platform_name in platforms:
            platform_spec = get_platform_spec(platform_name)
            click.echo(f"🎨 Transcoding for {platform_spec.name}...")

            transcoded_paths = transcoder.transcode_all(
                chunk_paths, output_dir, platform_spec
            )

            click.echo(f"✅ Created {len(transcoded_paths)} videos for {platform_spec.name}")
            click.echo(f"   Output: {transcoded_paths[0].parent}\n")

        # Step 5: Upload to YouTube (optional)
        if upload_youtube and "youtube" in platforms:
            try:
                from .youtube_uploader import YouTubeUploader, format_metadata_for_youtube

                # Get YouTube Shorts videos
                youtube_dir = output_dir / "youtube_shorts"
                youtube_videos = sorted(youtube_dir.glob("*.mp4"))

                if youtube_videos:
                    # Check if IMDb metadata exists
                    imdb_metadata = None
                    imdb_metadata_file = output_dir / f"{folder_name}_metadata.json"

                    if imdb_metadata_file.exists():
                        try:
                            with open(imdb_metadata_file, 'r') as f:
                                imdb_metadata = json.load(f)
                            click.echo(f"📊 Using IMDb metadata for upload info")
                        except Exception as e:
                            click.echo(f"⚠️  Could not load IMDb metadata: {e}")

                    # Determine if we should use IMDb metadata or CLI options
                    use_imdb = imdb_metadata is not None

                    # Check if user provided custom values (not defaults)
                    has_custom_title = youtube_title != "{filename} - Part {n}"
                    has_custom_description = youtube_description != ""
                    has_custom_tags = youtube_tags != ""

                    if use_imdb and not (has_custom_title or has_custom_description or has_custom_tags):
                        # Priority 2: Use IMDb metadata for all videos
                        click.echo(f"🎬 Auto-generating titles, descriptions, and tags from IMDb data")

                        # Upload each video with IMDb-generated metadata
                        from .youtube_uploader import UploadResult
                        results = []
                        total = len(youtube_videos)

                        click.echo(f"\n📺 Starting batch upload: {total} video(s)\n")

                        for i, video_path in enumerate(youtube_videos, start=1):
                            # Generate metadata for this chunk
                            metadata = format_metadata_for_youtube(
                                imdb_metadata,
                                chunk_number=i,
                                total_chunks=total,
                                title_template=youtube_title if has_custom_title else None,
                                description_override=youtube_description if has_custom_description else None
                            )

                            # Merge with custom tags if provided
                            if has_custom_tags:
                                custom_tags = [tag.strip() for tag in youtube_tags.split(",")]
                                metadata['tags'] = custom_tags + metadata['tags']
                                metadata['tags'] = list(dict.fromkeys(metadata['tags']))[:15]  # Remove dupes, limit to 15

                            # Upload single video
                            uploader = YouTubeUploader()
                            try:
                                result = uploader.upload_short(
                                    video_path=video_path,
                                    title=metadata['title'],
                                    description=metadata['description'],
                                    tags=metadata['tags'],
                                    privacy_status=youtube_privacy
                                )
                                results.append(result)
                                click.echo()  # Blank line between uploads
                            except Exception as e:
                                click.echo(f"❌ Upload failed: {video_path.name}")
                                click.echo(f"   Error: {e}\n")
                                continue

                        click.echo(f"✅ Batch upload complete: {len(results)}/{total} successful\n")
                    elif yt_source_metadata and not (has_custom_title or has_custom_description or has_custom_tags):
                        # Priority 3: Use YouTube source video metadata
                        click.echo(f"📺 Using source video metadata for upload info")
                        results = []
                        total = len(youtube_videos)
                        yt_title = yt_source_metadata['title']

                        # Trim description to YouTube's 5000 char limit, append #Shorts
                        shorts_suffix = "\n\n#Shorts"
                        raw_desc = yt_source_metadata.get('description', '')
                        trimmed_desc = raw_desc[:5000 - len(shorts_suffix)] + shorts_suffix

                        # Cap tags at YouTube's 15-tag limit
                        yt_tags = yt_source_metadata.get('tags', [])[:15]

                        click.echo(f"\n📺 Starting batch upload: {total} video(s)\n")

                        for i, video_path in enumerate(youtube_videos, start=1):
                            title = f"{yt_title} - Part {i}"
                            if len(title) > 100:
                                title = title[:97] + "..."

                            uploader = YouTubeUploader()
                            try:
                                result = uploader.upload_short(
                                    video_path=video_path,
                                    title=title,
                                    description=trimmed_desc,
                                    tags=yt_tags,
                                    privacy_status=youtube_privacy
                                )
                                results.append(result)
                                click.echo()
                            except Exception as e:
                                click.echo(f"❌ Upload failed: {video_path.name}")
                                click.echo(f"   Error: {e}\n")
                                continue

                        click.echo(f"✅ Batch upload complete: {len(results)}/{total} successful\n")

                    else:
                        # Priority 4: Use CLI options (original behavior)
                        tags = [tag.strip() for tag in youtube_tags.split(",")] if youtube_tags else []

                        # Initialize uploader and upload batch
                        uploader = YouTubeUploader()
                        results = uploader.upload_batch(
                            video_paths=youtube_videos,
                            title_template=youtube_title,
                            description=youtube_description,
                            tags=tags,
                            privacy_status=youtube_privacy
                        )

                    # Save upload metadata
                    if results:
                        uploader = YouTubeUploader()
                        metadata_path = output_dir / "youtube_uploads.json"
                        uploader.save_upload_metadata(results, metadata_path)

            except ValueError as e:
                # Missing credentials - show warning but continue
                click.echo(f"⚠️  YouTube upload skipped: {e}\n", err=True)
            except Exception as e:
                # Other errors - log but don't fail entire process
                click.echo(f"❌ YouTube upload failed: {e}\n", err=True)

        # Success summary
        click.echo("🎉 Processing complete!")
        click.echo(f"📁 Output directory: {output_dir.absolute()}")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)

    finally:
        # Cleanup temporary files
        if not keep_temp:
            downloader.cleanup()


if __name__ == "__main__":
    main()
