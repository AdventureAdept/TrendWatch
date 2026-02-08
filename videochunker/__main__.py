"""CLI entry point for videochunker."""

import logging
import shutil
import sys
from pathlib import Path

import click

from .chunker import VideoChunker
from .downloader import VideoDownloader
from .platforms import PlatformType, get_all_platforms, get_platform_spec
from .transcoder import VideoTranscoder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)


@click.command()
@click.argument("video_url")
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
    default=30,
    help="Chunk duration in seconds",
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
    help="Enable face detection for smart cropping (default: enabled)",
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
def main(
    video_url: str,
    platform: PlatformType,
    output: str,
    duration: int,
    max_chunks: int,
    smart_crop: bool,
    hflip: bool,
    keep_temp: bool,
):
    """Split videos from URLs into platform-specific reels.

    VIDEO_URL: URL of the video to download and process
    """
    click.echo(f"🎬 Video Chunker - Processing: {video_url}")
    click.echo(f"📱 Target platform(s): {platform}")
    click.echo(f"⏱️  Chunk duration: {duration}s")
    click.echo(f"📊 Max chunks: {max_chunks}")
    click.echo(f"🤖 Smart crop: {'enabled' if smart_crop else 'disabled'}")
    click.echo(f"🔄 Horizontal flip: {'enabled' if hflip else 'disabled'}\n")

    # Check FFmpeg availability
    if not shutil.which("ffmpeg"):
        click.echo("❌ Error: FFmpeg is not installed or not in PATH", err=True)
        click.echo("Install FFmpeg: https://ffmpeg.org/download.html", err=True)
        sys.exit(1)

    output_dir = Path(output)
    downloader = VideoDownloader()
    chunker = VideoChunker(chunk_duration=duration, max_chunks=max_chunks)
    transcoder = VideoTranscoder(smart_crop=smart_crop, hflip=hflip)

    try:
        # Step 1: Download video
        click.echo("📥 Downloading video...")
        video_path = downloader.download(video_url)
        click.echo(f"✅ Downloaded: {video_path.name}\n")

        # Step 2: Chunk video
        click.echo(f"✂️  Splitting into {duration}s chunks (max: {max_chunks})...")
        chunks_dir = Path(downloader.output_dir) / "chunks"
        chunk_paths = chunker.chunk(video_path, chunks_dir)
        click.echo(f"✅ Created {len(chunk_paths)} chunks\n")

        # Step 3: Transcode for platforms
        platforms = get_all_platforms() if platform == "all" else [platform]

        for platform_name in platforms:
            platform_spec = get_platform_spec(platform_name)
            click.echo(f"🎨 Transcoding for {platform_spec.name}...")

            transcoded_paths = transcoder.transcode_all(
                chunk_paths, output_dir, platform_spec
            )

            click.echo(f"✅ Created {len(transcoded_paths)} videos for {platform_spec.name}")
            click.echo(f"   Output: {transcoded_paths[0].parent}\n")

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
