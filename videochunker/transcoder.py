"""Video transcoding for platform-specific formats."""

import logging
import subprocess
from pathlib import Path

from .face_detector import MediaPipeFaceDetector, FaceDetectorConfig
from .platforms import PlatformSpec

logger = logging.getLogger(__name__)


class VideoTranscoder:
    """Transcodes video chunks to platform-specific formats."""

    def __init__(self, smart_crop: bool = True, hflip: bool = True):
        """Initialize transcoder.

        Args:
            smart_crop: Enable face detection for smart cropping (default: True)
            hflip: Apply horizontal flip effect (default: True)
        """
        self.smart_crop = smart_crop
        self.hflip = hflip
        # Initialize detector configuration
        self.detector_config = FaceDetectorConfig(
            min_detection_confidence=0.6,
            sample_frames=3,
            frame_positions=[0.25, 0.5, 0.75],
        )

    def transcode(
        self, input_path: Path, output_path: Path, platform_spec: PlatformSpec
    ) -> Path:
        """Transcode video to platform-specific format.

        Args:
            input_path: Path to input video chunk
            output_path: Path for output video
            platform_spec: Platform specification with encoding parameters

        Returns:
            Path to transcoded video

        Raises:
            Exception: If transcoding fails
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Determine crop position
        if self.smart_crop:
            try:
                # Use context manager for proper resource cleanup
                with MediaPipeFaceDetector(self.detector_config) as detector:
                    crop_x, crop_y = detector.get_smart_crop_position(
                        input_path, platform_spec.width, platform_spec.height
                    )
                # Use explicit crop position based on face detection
                crop_filter = f"crop={platform_spec.width}:{platform_spec.height}:{crop_x}:{crop_y}"
            except Exception as e:
                # Fallback to center crop if face detection fails
                logger.warning(f"Face detection failed for {input_path.name}: {e}")
                logger.info(f"Falling back to center crop for {input_path.name}")
                crop_filter = f"crop={platform_spec.width}:{platform_spec.height}"
        else:
            # Center crop (default behavior)
            crop_filter = f"crop={platform_spec.width}:{platform_spec.height}"

        # Build video filter chain
        filters = [
            f"scale={platform_spec.width}:{platform_spec.height}:force_original_aspect_ratio=increase",
            crop_filter,
        ]

        if self.hflip:
            filters.append("hflip")

        filters.append("setsar=1")
        filter_chain = ",".join(filters)

        # Build FFmpeg command with platform-specific settings
        cmd = [
            "ffmpeg",
            "-i",
            str(input_path),
            # Video filters: scale to fill and smart/center crop (no black bars)
            "-vf",
            filter_chain,
            # Video codec and settings
            "-c:v",
            platform_spec.video_codec,
            "-b:v",
            platform_spec.video_bitrate,
            "-pix_fmt",
            platform_spec.pixel_format,
            "-preset",
            "medium",
            "-profile:v",
            "high",
            "-level",
            "4.2",
            # Audio codec and settings
            "-c:a",
            platform_spec.audio_codec,
            "-b:a",
            platform_spec.audio_bitrate,
            "-ar",
            "44100",
            # Output settings
            "-movflags",
            "+faststart",  # Enable progressive streaming
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
            return output_path
        except subprocess.CalledProcessError as e:
            raise Exception(
                f"Failed to transcode {input_path.name}: {e.stderr}"
            ) from e

    def transcode_all(
        self, chunk_paths: list[Path], output_dir: Path, platform_spec: PlatformSpec
    ) -> list[Path]:
        """Transcode all chunks to platform-specific format.

        Args:
            chunk_paths: List of input chunk paths
            output_dir: Directory for output videos
            platform_spec: Platform specification

        Returns:
            List of transcoded video paths
        """
        platform_dir = output_dir / platform_spec.name.lower().replace(" ", "_")
        platform_dir.mkdir(parents=True, exist_ok=True)

        transcoded_paths = []
        for chunk_path in chunk_paths:
            output_path = platform_dir / f"{chunk_path.stem}_{platform_spec.name.lower().replace(' ', '_')}.mp4"
            transcoded_path = self.transcode(chunk_path, output_path, platform_spec)
            transcoded_paths.append(transcoded_path)

        return transcoded_paths
