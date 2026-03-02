"""Platform-specific specifications for video output."""

from dataclasses import dataclass
from typing import Literal


@dataclass
class PlatformSpec:
    """Specification for a social media platform."""

    name: str
    aspect_ratio: str
    width: int
    height: int
    max_duration: int  # Technical maximum in seconds
    recommended_duration: int  # Recommended duration for best performance (seconds)
    video_codec: str
    audio_codec: str
    video_bitrate: str
    audio_bitrate: str
    pixel_format: str


# Platform specifications
# Note: max_duration is the technical limit, recommended_duration is for optimal engagement
PLATFORMS = {
    "youtube": PlatformSpec(
        name="YouTube Shorts",
        aspect_ratio="9:16",
        width=1080,
        height=1920,
        max_duration=180,  # Technical limit (3 min as of Oct 2024)
        recommended_duration=90,  # 60-90s recommended for best performance
        video_codec="libx264",
        audio_codec="aac",
        video_bitrate="8000k",
        audio_bitrate="192k",
        pixel_format="yuv420p",
    ),
    "instagram": PlatformSpec(
        name="Instagram Reels",
        aspect_ratio="9:16",
        width=1080,
        height=1920,
        max_duration=90,  # Technical limit
        recommended_duration=90,  # 60-90s recommended for best performance
        video_codec="libx264",
        audio_codec="aac",
        video_bitrate="8000k",
        audio_bitrate="192k",
        pixel_format="yuv420p",
    ),
    "facebook": PlatformSpec(
        name="Facebook Reels",
        aspect_ratio="9:16",
        width=1080,
        height=1920,
        max_duration=90,  # Technical limit
        recommended_duration=90,  # 60-90s recommended for best performance
        video_codec="libx264",
        audio_codec="aac",
        video_bitrate="8000k",
        audio_bitrate="192k",
        pixel_format="yuv420p",
    ),
    "tiktok": PlatformSpec(
        name="TikTok",
        aspect_ratio="9:16",
        width=1080,
        height=1920,
        max_duration=600,  # 10 minutes (in-app recording limit)
        recommended_duration=60,  # 60-90s recommended (algorithm favors 21-34s)
        video_codec="libx264",
        audio_codec="aac",
        video_bitrate="8000k",
        audio_bitrate="192k",
        pixel_format="yuv420p",
    ),
}

PlatformType = Literal["youtube", "instagram", "facebook", "tiktok", "all"]


def get_platform_spec(platform: str) -> PlatformSpec:
    """Get platform specification by name.

    Args:
        platform: Platform name (youtube, instagram, facebook, tiktok)

    Returns:
        PlatformSpec for the requested platform

    Raises:
        ValueError: If platform is not supported
    """
    if platform not in PLATFORMS:
        raise ValueError(
            f"Unsupported platform: {platform}. "
            f"Supported platforms: {', '.join(PLATFORMS.keys())}"
        )
    return PLATFORMS[platform]


def get_all_platforms() -> list[str]:
    """Get list of all supported platform names."""
    return list(PLATFORMS.keys())
