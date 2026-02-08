"""Face detection for smart video cropping."""

import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np


class FaceDetector:
    """Detects faces in video frames for intelligent cropping."""

    def __init__(self):
        """Initialize face detector with Haar Cascade classifier."""
        # Load pre-trained face detection model (Haar Cascade)
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

    def extract_frame(self, video_path: Path, timestamp: float = None) -> np.ndarray:
        """Extract a frame from video at specified timestamp.

        Args:
            video_path: Path to video file
            timestamp: Time in seconds to extract frame (default: middle of video)

        Returns:
            Frame as numpy array (BGR format)

        Raises:
            Exception: If frame extraction fails
        """
        if timestamp is None:
            # Get video duration and extract middle frame
            duration = self._get_video_duration(video_path)
            timestamp = duration / 2

        # Use FFmpeg to extract frame
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        cmd = [
            "ffmpeg",
            "-ss",
            str(timestamp),
            "-i",
            str(video_path),
            "-vframes",
            "1",
            "-q:v",
            "2",
            "-y",
            tmp_path,
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            frame = cv2.imread(tmp_path)
            Path(tmp_path).unlink()  # Clean up temp file
            return frame
        except Exception as e:
            raise Exception(f"Failed to extract frame: {str(e)}") from e

    def _get_video_duration(self, video_path: Path) -> float:
        """Get video duration in seconds."""
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())

    def detect_faces(self, frame: np.ndarray) -> list[tuple[int, int, int, int]]:
        """Detect faces in a frame.

        Args:
            frame: Frame as numpy array (BGR format)

        Returns:
            List of face bounding boxes as (x, y, width, height) tuples
        """
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
        )

        return [tuple(face) for face in faces]

    def calculate_crop_region(
        self,
        frame_width: int,
        frame_height: int,
        faces: list[tuple[int, int, int, int]],
        target_width: int,
        target_height: int,
    ) -> tuple[int, int]:
        """Calculate optimal crop position to include faces.

        Args:
            frame_width: Original frame width
            frame_height: Original frame height
            faces: List of face bounding boxes (x, y, w, h)
            target_width: Target crop width
            target_height: Target crop height

        Returns:
            Tuple of (crop_x, crop_y) - top-left corner of crop region
        """
        if not faces:
            # No faces detected, return center crop
            crop_x = (frame_width - target_width) // 2
            crop_y = (frame_height - target_height) // 2
            return max(0, crop_x), max(0, crop_y)

        # Calculate center of all faces
        face_centers_x = []
        face_centers_y = []

        for x, y, w, h in faces:
            center_x = x + w // 2
            center_y = y + h // 2
            face_centers_x.append(center_x)
            face_centers_y.append(center_y)

        # Average center point of all faces
        avg_face_x = sum(face_centers_x) // len(face_centers_x)
        avg_face_y = sum(face_centers_y) // len(face_centers_y)

        # Calculate crop position centered on faces
        crop_x = avg_face_x - (target_width // 2)
        crop_y = avg_face_y - (target_height // 2)

        # Ensure crop stays within frame bounds
        crop_x = max(0, min(crop_x, frame_width - target_width))
        crop_y = max(0, min(crop_y, frame_height - target_height))

        return crop_x, crop_y

    def get_smart_crop_position(
        self,
        video_path: Path,
        target_width: int,
        target_height: int,
    ) -> tuple[int, int]:
        """Get smart crop position based on face detection.

        Args:
            video_path: Path to video file
            target_width: Target crop width
            target_height: Target crop height

        Returns:
            Tuple of (crop_x, crop_y) for FFmpeg crop filter
        """
        # Extract middle frame
        frame = self.extract_frame(video_path)

        if frame is None:
            # Fallback to center crop
            return 0, 0

        frame_height, frame_width = frame.shape[:2]

        # Detect faces
        faces = self.detect_faces(frame)

        # Calculate optimal crop region
        # First, calculate what the scaled dimensions will be
        scale_ratio = max(target_width / frame_width, target_height / frame_height)
        scaled_width = int(frame_width * scale_ratio)
        scaled_height = int(frame_height * scale_ratio)

        # Calculate crop position on scaled frame
        crop_x, crop_y = self.calculate_crop_region(
            scaled_width, scaled_height, faces, target_width, target_height
        )

        return crop_x, crop_y
