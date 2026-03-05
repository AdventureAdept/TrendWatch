"""Face detection for smart video cropping using MediaPipe."""

import logging
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core import base_options as base_options_module
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FaceDetectorConfig:
    """Configuration for MediaPipe face detection.

    Attributes:
        min_detection_confidence: Minimum confidence value [0.0, 1.0] for face detection
        sample_frames: Number of frames to sample across video chunk
        frame_positions: Relative positions [0.0, 1.0] in video to sample frames
    """
    min_detection_confidence: float = 0.6
    sample_frames: int = 3
    frame_positions: list[float] = None

    def __post_init__(self):
        """Initialize default frame positions if not provided."""
        if self.frame_positions is None:
            self.frame_positions = [0.25, 0.5, 0.75]

        # Validate configuration
        if not 0.0 <= self.min_detection_confidence <= 1.0:
            raise ValueError("min_detection_confidence must be between 0.0 and 1.0")
        if len(self.frame_positions) != self.sample_frames:
            raise ValueError("frame_positions length must match sample_frames")


@dataclass
class DetectionResult:
    """Face detection result with metadata.

    Attributes:
        x, y: Top-left corner of bounding box (in pixels)
        width, height: Dimensions of bounding box (in pixels)
        confidence: Detection confidence score [0.0, 1.0]
        keypoints: Facial keypoints (if available)
    """
    x: int
    y: int
    width: int
    height: int
    confidence: float
    keypoints: dict[str, tuple[int, int]] = None

    def __post_init__(self):
        """Initialize keypoints if not provided."""
        if self.keypoints is None:
            self.keypoints = {}

    @property
    def center_x(self) -> int:
        """Return x coordinate of bounding box center."""
        return self.x + self.width // 2

    @property
    def center_y(self) -> int:
        """Return y coordinate of bounding box center."""
        return self.y + self.height // 2

    @property
    def eye_center(self) -> tuple[int, int]:
        """Return center point between eyes for more stable face centering."""
        if 'right_eye' in self.keypoints and 'left_eye' in self.keypoints:
            right_eye = self.keypoints['right_eye']
            left_eye = self.keypoints['left_eye']
            center_x = (right_eye[0] + left_eye[0]) // 2
            center_y = (right_eye[1] + left_eye[1]) // 2
            return (center_x, center_y)
        # Fallback to bbox center if eyes not detected
        return (self.center_x, self.center_y)


class MediaPipeFaceDetector:
    """Face detector using Google MediaPipe Tasks API."""

    def __init__(self, config: Optional[FaceDetectorConfig] = None):
        """Initialize MediaPipe face detector.

        Args:
            config: Detection configuration (uses defaults if None)
        """
        self.config = config or FaceDetectorConfig()
        self.detector = None

    def __enter__(self):
        """Initialize detector resources (context manager entry)."""
        # Locate the bundled model file
        model_path = Path(__file__).parent / "models" / "face_detection_short_range.tflite"
        if not model_path.exists():
            raise FileNotFoundError(
                f"MediaPipe face detection model not found at {model_path}. "
                "Download it from https://storage.googleapis.com/mediapipe-models/"
                "face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite"
            )

        base_options = base_options_module.BaseOptions(
            model_asset_path=str(model_path)
        )

        options = vision.FaceDetectorOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            min_detection_confidence=self.config.min_detection_confidence,
        )

        self.detector = vision.FaceDetector.create_from_options(options)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up detector resources (context manager exit)."""
        if self.detector:
            self.detector.close()
            self.detector = None

    def extract_frame(self, video_path: Path, timestamp: Optional[float] = None) -> Optional[np.ndarray]:
        """Extract a frame from video at specified timestamp.

        Args:
            video_path: Path to video file
            timestamp: Time in seconds to extract frame (default: middle of video)

        Returns:
            Frame as numpy array (BGR format), or None if extraction fails
        """
        try:
            if timestamp is None:
                # Get video duration and extract middle frame
                duration = self._get_video_duration(video_path)
                timestamp = duration / 2

            # Use FFmpeg to extract frame
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            cmd = [
                "ffmpeg",
                "-analyzeduration", "100M",
                "-probesize", "100M",
                "-ss", str(timestamp),
                "-i", str(video_path),
                "-vframes", "1",
                "-q:v", "2",
                "-y",
                tmp_path,
            ]

            subprocess.run(cmd, capture_output=True, check=True)
            frame = cv2.imread(tmp_path)
            Path(tmp_path).unlink()  # Clean up temp file
            return frame

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg frame extraction failed: {e.stderr}")
            return None
        except Exception as e:
            logger.error(f"Failed to extract frame: {e}")
            return None

    def _get_video_duration(self, video_path: Path) -> float:
        """Get video duration in seconds.

        Args:
            video_path: Path to video file

        Returns:
            Duration in seconds

        Raises:
            subprocess.CalledProcessError: If ffprobe fails
        """
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())

    def detect_faces(self, frame: np.ndarray) -> list[DetectionResult]:
        """Detect faces in a frame using MediaPipe.

        Args:
            frame: Frame as numpy array (BGR format)

        Returns:
            List of DetectionResult objects, sorted by confidence (highest first)
        """
        if self.detector is None:
            raise RuntimeError("Detector not initialized. Use 'with' statement or call __enter__().")

        if frame is None or frame.size == 0:
            return []

        # Convert BGR to RGB (MediaPipe expects RGB)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_height, frame_width = frame.shape[:2]

        # Create MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        # Run detection
        detection_result = self.detector.detect(mp_image)

        if not detection_result.detections:
            return []

        # Convert detections to DetectionResult objects
        detection_results = []
        for detection in detection_result.detections:
            # Get bounding box (normalized coordinates [0.0, 1.0])
            bbox = detection.bounding_box

            # Convert to absolute pixel coordinates
            x = int(bbox.origin_x)
            y = int(bbox.origin_y)
            width = int(bbox.width)
            height = int(bbox.height)

            # Extract keypoints if available
            keypoints = {}
            if detection.keypoints:
                keypoint_names = ['right_eye', 'left_eye', 'nose_tip', 'mouth', 'right_ear', 'left_ear']
                for i, keypoint in enumerate(detection.keypoints):
                    if i < len(keypoint_names):
                        kp_x = int(keypoint.x * frame_width)
                        kp_y = int(keypoint.y * frame_height)
                        keypoints[keypoint_names[i]] = (kp_x, kp_y)

            # Get confidence score (first category's score)
            confidence = detection.categories[0].score if detection.categories else 0.0

            detection_results.append(DetectionResult(
                x=x, y=y, width=width, height=height,
                confidence=confidence,
                keypoints=keypoints
            ))

        # Sort by confidence (highest first)
        detection_results.sort(key=lambda d: d.confidence, reverse=True)
        return detection_results

    def detect_faces_multi_frame(self, video_path: Path) -> list[DetectionResult]:
        """Detect faces across multiple frames in video.

        Samples frames at configured positions and aggregates all detections.

        Args:
            video_path: Path to video file

        Returns:
            List of all DetectionResult objects from all frames, sorted by confidence
        """
        try:
            duration = self._get_video_duration(video_path)
        except Exception as e:
            logger.warning(f"Failed to get video duration: {e}")
            # Fallback to single middle frame
            return self.detect_faces_single_frame(video_path)

        all_detections = []

        for position in self.config.frame_positions:
            timestamp = duration * position
            frame = self.extract_frame(video_path, timestamp)

            if frame is not None:
                detections = self.detect_faces(frame)
                all_detections.extend(detections)

        # Sort all detections by confidence
        all_detections.sort(key=lambda d: d.confidence, reverse=True)
        return all_detections

    def detect_faces_single_frame(self, video_path: Path, timestamp: Optional[float] = None) -> list[DetectionResult]:
        """Detect faces in a single frame (fallback method).

        Args:
            video_path: Path to video file
            timestamp: Timestamp to extract frame (default: middle)

        Returns:
            List of DetectionResult objects
        """
        frame = self.extract_frame(video_path, timestamp)
        if frame is None:
            return []
        return self.detect_faces(frame)

    def calculate_crop_region(
        self,
        frame_width: int,
        frame_height: int,
        detections: list[DetectionResult],
        target_width: int,
        target_height: int,
    ) -> tuple[int, int]:
        """Calculate optimal crop position to include detected faces.

        Uses eye centers (if available) for more stable centering than bbox centers.
        Weights crop calculation by detection confidence.

        Args:
            frame_width: Scaled frame width
            frame_height: Scaled frame height
            detections: List of face detections
            target_width: Target crop width
            target_height: Target crop height

        Returns:
            Tuple of (crop_x, crop_y) - top-left corner of crop region
        """
        if not detections:
            # No faces detected, return center crop
            crop_x = (frame_width - target_width) // 2
            crop_y = (frame_height - target_height) // 2
            return max(0, crop_x), max(0, crop_y)

        # Use eye centers for more stable positioning
        # Weight by confidence to prioritize high-confidence detections
        weighted_x = 0.0
        weighted_y = 0.0
        total_weight = 0.0

        for detection in detections:
            eye_x, eye_y = detection.eye_center
            confidence = detection.confidence

            weighted_x += eye_x * confidence
            weighted_y += eye_y * confidence
            total_weight += confidence

        # Calculate weighted average center point
        if total_weight > 0:
            avg_face_x = int(weighted_x / total_weight)
            avg_face_y = int(weighted_y / total_weight)
        else:
            # Fallback to simple average
            avg_face_x = int(sum(d.eye_center[0] for d in detections) / len(detections))
            avg_face_y = int(sum(d.eye_center[1] for d in detections) / len(detections))

        # Calculate crop position centered on weighted face center
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

        Main entry point for face-based cropping. Analyzes multiple frames
        and returns optimal crop coordinates for FFmpeg.

        Args:
            video_path: Path to video file
            target_width: Target crop width (e.g., 1080 for 9:16)
            target_height: Target crop height (e.g., 1920 for 9:16)

        Returns:
            Tuple of (crop_x, crop_y) for FFmpeg crop filter
        """
        # Detect faces across multiple frames
        detections = self.detect_faces_multi_frame(video_path)

        if not detections:
            logger.info(f"No faces detected in {video_path.name}, using center crop")
            return 0, 0  # FFmpeg will center crop by default

        logger.info(f"Detected {len(detections)} face(s) in {video_path.name} "
                   f"(best confidence: {detections[0].confidence:.2f})")

        # Get original video dimensions
        # Extract a frame to get dimensions
        frame = self.extract_frame(video_path)
        if frame is None:
            logger.warning(f"Could not extract frame from {video_path.name}, using center crop")
            return 0, 0

        original_height, original_width = frame.shape[:2]

        # Calculate scaled dimensions (matching FFmpeg scale filter behavior)
        # FFmpeg: scale=target_w:target_h:force_original_aspect_ratio=increase
        scale_ratio = max(target_width / original_width, target_height / original_height)
        scaled_width = int(original_width * scale_ratio)
        scaled_height = int(original_height * scale_ratio)

        # CRITICAL FIX: Scale face coordinates to match scaled frame dimensions
        # The detections have coordinates in original frame space, need to scale them
        scaled_detections = []
        for detection in detections:
            scaled_detection = DetectionResult(
                x=int(detection.x * scale_ratio),
                y=int(detection.y * scale_ratio),
                width=int(detection.width * scale_ratio),
                height=int(detection.height * scale_ratio),
                confidence=detection.confidence,
                keypoints={
                    name: (int(x * scale_ratio), int(y * scale_ratio))
                    for name, (x, y) in detection.keypoints.items()
                } if detection.keypoints else {}
            )
            scaled_detections.append(scaled_detection)

        # Calculate crop position on scaled frame with scaled detections
        crop_x, crop_y = self.calculate_crop_region(
            scaled_width, scaled_height, scaled_detections, target_width, target_height
        )

        return crop_x, crop_y


# Backwards compatibility: alias for old class name
FaceDetector = MediaPipeFaceDetector
