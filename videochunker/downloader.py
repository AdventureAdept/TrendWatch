"""Video downloader using yt-dlp."""

import os
import tempfile
from pathlib import Path

import yt_dlp


class VideoDownloader:
    """Downloads videos from URLs using yt-dlp."""

    def __init__(self, output_dir: str | None = None):
        """Initialize downloader.

        Args:
            output_dir: Directory to save downloaded videos. If None, uses temp directory.
        """
        self.output_dir = output_dir or tempfile.mkdtemp(prefix="videochunker_")

    def download(self, url: str) -> Path:
        """Download video from URL.

        Args:
            url: Video URL to download

        Returns:
            Path to downloaded video file

        Raises:
            Exception: If download fails
        """
        output_template = os.path.join(self.output_dir, "%(title)s.%(ext)s")

        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": output_template,
            "quiet": False,
            "no_warnings": False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                return Path(filename)
        except Exception as e:
            raise Exception(f"Failed to download video: {str(e)}") from e

    def cleanup(self):
        """Clean up temporary download directory if it was created."""
        if self.output_dir.startswith(tempfile.gettempdir()):
            import shutil

            shutil.rmtree(self.output_dir, ignore_errors=True)
