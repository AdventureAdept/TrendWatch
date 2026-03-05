"""Platform-specific specifications for video output."""

from dataclasses import dataclass
from typing import Literal


@dataclass
class PlatformSpec:
    """Specification for a social media platform."""

    name: str
    width: int
    height: int
    video_codec: str
    audio_codec: str
    video_bitrate: str
    audio_bitrate: str
    pixel_format: str


PLATFORMS = {
    "youtube": PlatformSpec(
        name="YouTube Shorts",
        width=1080,
        height=1920,
        video_codec="libx264",
        audio_codec="aac",
        video_bitrate="8000k",
        audio_bitrate="192k",
        pixel_format="yuv420p",
    ),
    "instagram": PlatformSpec(
        name="Instagram Reels",
        width=1080,
        height=1920,
        video_codec="libx264",
        audio_codec="aac",
        video_bitrate="8000k",
        audio_bitrate="192k",
        pixel_format="yuv420p",
    ),
    "facebook": PlatformSpec(
        name="Facebook Reels",
        width=1080,
        height=1920,
        video_codec="libx264",
        audio_codec="aac",
        video_bitrate="8000k",
        audio_bitrate="192k",
        pixel_format="yuv420p",
    ),
    "tiktok": PlatformSpec(
        name="TikTok",
        width=1080,
        height=1920,
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
