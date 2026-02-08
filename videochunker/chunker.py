"""Video chunking into fixed-duration segments."""

import subprocess
from pathlib import Path


class VideoChunker:
    """Splits videos into fixed-duration chunks using FFmpeg."""

    def __init__(self, chunk_duration: int = 30, max_chunks: int | None = None):
        """Initialize chunker.

        Args:
            chunk_duration: Duration of each chunk in seconds (default: 30)
            max_chunks: Maximum number of chunks to create (default: None - create all chunks)
        """
        self.chunk_duration = chunk_duration
        self.max_chunks = max_chunks

    def get_video_duration(self, input_path: Path) -> float:
        """Get video duration in seconds using FFprobe.

        Args:
            input_path: Path to input video

        Returns:
            Duration in seconds

        Raises:
            Exception: If unable to get duration
        """
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(input_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except Exception as e:
            raise Exception(f"Failed to get video duration: {str(e)}") from e

    def chunk(self, input_path: Path, output_dir: Path) -> list[Path]:
        """Split video into fixed-duration chunks.

        Args:
            input_path: Path to input video
            output_dir: Directory to save chunks

        Returns:
            List of paths to chunk files

        Raises:
            Exception: If chunking fails
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get total duration
        duration = self.get_video_duration(input_path)
        num_chunks = int(duration // self.chunk_duration) + (
            1 if duration % self.chunk_duration > 0 else 0
        )

        # Limit to max_chunks if specified
        if self.max_chunks is not None:
            num_chunks = min(num_chunks, self.max_chunks)

        chunk_paths = []
        input_stem = input_path.stem

        for i in range(num_chunks):
            start_time = i * self.chunk_duration
            output_path = output_dir / f"{input_stem}_chunk_{i+1:03d}.mp4"

            # Use FFmpeg to extract chunk
            cmd = [
                "ffmpeg",
                "-i",
                str(input_path),
                "-ss",
                str(start_time),
                "-t",
                str(self.chunk_duration),
                "-c",
                "copy",  # Copy codec (fast, no re-encoding)
                "-avoid_negative_ts",
                "1",
                "-y",  # Overwrite output file
                str(output_path),
            ]

            try:
                subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                chunk_paths.append(output_path)
            except subprocess.CalledProcessError as e:
                raise Exception(
                    f"Failed to create chunk {i+1}: {e.stderr}"
                ) from e

        return chunk_paths
