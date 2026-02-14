"""YOLO-based smart cropping for vertical video conversion."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from scenedetect import detect, ContentDetector
from ultralytics import YOLO

logger = logging.getLogger(__name__)


@dataclass
class CropStrategy:
    """Cropping strategy for a scene."""

    method: str  # "track" or "letterbox"
    x_offset: int  # Horizontal offset for crop
    confidence: float  # Detection confidence


class YOLOCropper:
    """Smart vertical cropping using YOLOv8 person detection and scene analysis."""

    def __init__(self, model_name: str = "yolov8n.pt", confidence_threshold: float = 0.3):
        """Initialize YOLO cropper.

        Args:
            model_name: YOLOv8 model to use (n=nano, s=small, m=medium, etc.)
            confidence_threshold: Minimum confidence for person detection
        """
        self.confidence_threshold = confidence_threshold

        logger.info(f"Loading YOLO model: {model_name}")
        self.model = YOLO(model_name)
        logger.info("✅ YOLO model loaded")

    def get_smart_crop_position(
        self,
        video_path: Path,
        target_width: int,
        target_height: int,
    ) -> tuple[int, int]:
        """Get smart crop position for video using YOLO person detection.

        This performs scene-by-scene analysis to determine optimal crop position.

        Args:
            video_path: Path to video file
            target_width: Target crop width (e.g., 1080 for 9:16)
            target_height: Target crop height (e.g., 1920 for 9:16)

        Returns:
            Tuple of (x_offset, y_offset) for crop position

        Note:
            This is a simplified version that returns a single crop position.
            For full scene-by-scene tracking, use get_scene_crop_strategies().
        """
        logger.info(f"Analyzing video with YOLO: {video_path.name}")

        # Open video
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            logger.warning(f"Could not open video: {video_path}")
            return self._center_crop(cap, target_width, target_height)

        # Get video properties
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Sample frames for analysis (middle 3 frames)
        sample_positions = [0.25, 0.5, 0.75]
        detections = []

        for pos in sample_positions:
            frame_num = int(total_frames * pos)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()

            if not ret:
                continue

            # Detect people in frame
            results = self.model(frame, verbose=False)

            for result in results:
                boxes = result.boxes
                for box in boxes:
                    # Check if it's a person (class 0 in COCO)
                    if int(box.cls[0]) == 0 and float(box.conf[0]) >= self.confidence_threshold:
                        # Get bounding box
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        center_x = (x1 + x2) / 2
                        confidence = float(box.conf[0])

                        detections.append({
                            'center_x': center_x,
                            'confidence': confidence,
                        })

        cap.release()

        # Calculate crop position based on detections
        if detections:
            # Weight by confidence
            total_weight = sum(d['confidence'] for d in detections)
            weighted_x = sum(d['center_x'] * d['confidence'] for d in detections) / total_weight

            # Calculate crop x position to center on detected person
            crop_x = int(weighted_x - (target_width / 2))

            # Ensure crop stays within bounds
            crop_x = max(0, min(crop_x, frame_width - target_width))
            crop_y = 0  # Vertical videos typically use full height

            logger.info(f"✅ Detected {len(detections)} person(s) with avg confidence: {total_weight/len(detections):.2f}")
            return crop_x, crop_y
        else:
            logger.warning("No people detected, using center crop")
            return self._center_crop_coords(frame_width, frame_height, target_width, target_height)

    def detect_scenes(self, video_path: Path) -> list[tuple[float, float]]:
        """Detect scene boundaries in video.

        Args:
            video_path: Path to video file

        Returns:
            List of (start_time, end_time) tuples for each scene
        """
        logger.info(f"Detecting scenes in {video_path.name}")

        # Use scenedetect to find scene boundaries
        scene_list = detect(str(video_path), ContentDetector())

        scenes = [(scene[0].get_seconds(), scene[1].get_seconds()) for scene in scene_list]

        logger.info(f"✅ Detected {len(scenes)} scenes")
        return scenes

    def get_scene_crop_strategies(
        self,
        video_path: Path,
        target_width: int,
        target_height: int,
    ) -> list[CropStrategy]:
        """Get crop strategy for each scene in the video.

        This is the advanced mode that analyzes each scene separately.

        Args:
            video_path: Path to video file
            target_width: Target crop width
            target_height: Target crop height

        Returns:
            List of CropStrategy objects, one per scene
        """
        scenes = self.detect_scenes(video_path)

        if not scenes:
            # No scenes detected, treat as single scene
            logger.warning("No scenes detected, using single crop strategy")
            x, y = self.get_smart_crop_position(video_path, target_width, target_height)
            return [CropStrategy(method="track", x_offset=x, confidence=1.0)]

        strategies = []
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        for scene_start, scene_end in scenes:
            # Sample middle frame of scene
            mid_time = (scene_start + scene_end) / 2
            frame_num = int(mid_time * fps)

            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()

            if not ret:
                strategies.append(CropStrategy(
                    method="letterbox",
                    x_offset=self._center_crop_coords(frame_width, frame_height, target_width, target_height)[0],
                    confidence=0.0
                ))
                continue

            # Detect people in this scene
            results = self.model(frame, verbose=False)

            person_detections = []
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    if int(box.cls[0]) == 0 and float(box.conf[0]) >= self.confidence_threshold:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        width = x2 - x1
                        height = y2 - y1
                        center_x = (x1 + x2) / 2

                        person_detections.append({
                            'center_x': center_x,
                            'width': width,
                            'height': height,
                            'confidence': float(box.conf[0]),
                        })

            if person_detections:
                # Get best detection
                best = max(person_detections, key=lambda d: d['confidence'])

                # Decide strategy based on person size
                # If person is too wide or too far, use letterbox
                person_width_ratio = best['width'] / frame_width

                if person_width_ratio > 0.7:  # Person takes up most of frame width
                    method = "letterbox"
                    x_offset = 0
                else:
                    method = "track"
                    x_offset = int(best['center_x'] - (target_width / 2))
                    x_offset = max(0, min(x_offset, frame_width - target_width))

                strategies.append(CropStrategy(
                    method=method,
                    x_offset=x_offset,
                    confidence=best['confidence']
                ))
            else:
                # No person detected, use center crop with letterbox
                strategies.append(CropStrategy(
                    method="letterbox",
                    x_offset=self._center_crop_coords(frame_width, frame_height, target_width, target_height)[0],
                    confidence=0.0
                ))

        cap.release()
        logger.info(f"✅ Generated {len(strategies)} crop strategies")
        return strategies

    @staticmethod
    def _center_crop(cap, target_width: int, target_height: int) -> tuple[int, int]:
        """Calculate center crop position."""
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        crop_x = (frame_width - target_width) // 2
        crop_y = (frame_height - target_height) // 2

        return max(0, crop_x), max(0, crop_y)

    @staticmethod
    def _center_crop_coords(frame_width: int, frame_height: int, target_width: int, target_height: int) -> tuple[int, int]:
        """Calculate center crop coordinates."""
        crop_x = (frame_width - target_width) // 2
        crop_y = (frame_height - target_height) // 2

        return max(0, crop_x), max(0, crop_y)
