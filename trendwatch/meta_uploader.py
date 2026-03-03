"""Meta Graph API client for uploading Facebook Reels and Instagram Reels.

This module provides long-lived access token authentication (manual setup)
and batch upload functionality for Facebook Reels and Instagram Reels
using the Meta Graph API v21.0.
"""

import json
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import requests

# Meta Graph API base URL
GRAPH_API_BASE = "https://graph.facebook.com/v21.0"

# Resumable upload host (shared by Facebook and Instagram)
RUPLOAD_HOST = "https://rupload.facebook.com"

# Default config directory
CONFIG_DIR = Path.home() / ".trendwatch"

# Chunk size for Facebook resumable upload (10 MB)
CHUNK_SIZE = 10 * 1024 * 1024

# Maximum poll attempts for Instagram status check (30 × 5s = 2.5 min)
MAX_POLL_ATTEMPTS = 30
POLL_INTERVAL = 5  # seconds

# Privacy value map for Facebook Reels
FB_PRIVACY_MAP = {
    "public": "EVERYONE",
    "friends": "FRIENDS",
    "only_me": "SELF",
}


@dataclass
class UploadResult:
    """Result from a single video upload."""

    video_id: str
    video_url: str
    title: str
    privacy_status: str
    uploaded_at: str
    file_path: str
    platform: str  # "facebook" or "instagram"


class MetaUploader:
    """Client for uploading Reels to Facebook and Instagram via Meta Graph API."""

    def __init__(self):
        """Initialize uploader with Meta credentials from environment variables.

        Reads META_ACCESS_TOKEN, META_PAGE_ID, and META_IG_USER_ID from
        the environment (loaded from ~/.trendwatch/.env by the CLI).

        Raises:
            ValueError: If META_ACCESS_TOKEN is not set, with setup instructions.
        """
        self.access_token = os.getenv("META_ACCESS_TOKEN", "")
        self.page_id = os.getenv("META_PAGE_ID", "")
        self.ig_user_id = os.getenv("META_IG_USER_ID", "")

        if not self.access_token:
            raise ValueError(
                "Meta credentials not found.\n\n"
                "To enable Facebook/Instagram uploads, follow these steps:\n\n"
                "1. Go to Meta for Developers:\n"
                "   https://developers.facebook.com\n\n"
                "2. Create an app → add 'Facebook Login' and\n"
                "   'Instagram Graph API' products\n\n"
                "3. Use Graph API Explorer to generate a long-lived User\n"
                "   Access Token with scopes:\n"
                "   publish_video, pages_manage_posts, pages_show_list,\n"
                "   instagram_content_publish\n\n"
                "4. Get your Page ID and Instagram User ID:\n"
                "   Run GET /me/accounts in Graph Explorer\n\n"
                "5. Save credentials:\n"
                f"   mkdir -p {CONFIG_DIR}\n"
                f"   cat >> {CONFIG_DIR / '.env'} << 'EOF'\n"
                "   META_ACCESS_TOKEN=YOUR_TOKEN\n"
                "   META_PAGE_ID=YOUR_PAGE_ID\n"
                "   META_IG_USER_ID=YOUR_IG_USER_ID\n"
                "   EOF\n"
            )

    # ------------------------------------------------------------------
    # Facebook Reels
    # ------------------------------------------------------------------

    def upload_facebook_reel(
        self,
        video_path: Path,
        title: str = "",
        description: str = "",
        tags: Optional[List[str]] = None,
        privacy: str = "public",
    ) -> UploadResult:
        """Upload a single video to a Facebook Page using multipart upload.

        Uses the /{page_id}/videos endpoint with direct multipart upload,
        which avoids the rupload.facebook.com resumable flow that requires
        pages with established Reels eligibility.

        Args:
            video_path: Path to video file.
            title: Video title.
            description: Video description / caption text.
            tags: List of hashtag strings (without #).
            privacy: "public", "friends", or "only_me".

        Returns:
            UploadResult with video ID and URL.

        Raises:
            FileNotFoundError: If video file doesn't exist.
            RuntimeError: On API or upload errors.
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if not self.page_id:
            raise ValueError(
                "META_PAGE_ID not set in ~/.trendwatch/.env (required for --u-fb)"
            )

        file_size = video_path.stat().st_size
        fb_privacy = FB_PRIVACY_MAP.get(privacy, "EVERYONE")

        # Build caption from title + description + hashtags
        caption_parts = []
        if title:
            caption_parts.append(title)
        if description:
            caption_parts.append(description)
        if tags:
            hashtags = " ".join(f"#{t.lstrip('#')}" for t in tags)
            caption_parts.append(hashtags)
        caption = "\n\n".join(caption_parts)

        print(f"📤 Uploading Facebook video: {title or video_path.name}")
        print(f"   File: {video_path.name}  ({file_size / 1024 / 1024:.1f} MB)")

        with open(video_path, "rb") as f:
            resp = requests.post(
                f"{GRAPH_API_BASE}/{self.page_id}/videos",
                data={
                    "access_token": self.access_token,
                    "title": title[:255] if title else "",
                    "description": caption[:2200] if caption else "",
                    "privacy": json.dumps({"value": fb_privacy}),
                },
                files={"source": (video_path.name, f, "video/mp4")},
                timeout=300,
            )
        self._raise_for_graph_error(resp, "upload video")

        video_id = resp.json()["id"]
        video_url = f"https://www.facebook.com/video/{video_id}"

        print(f"✅ Facebook video uploaded!")
        print(f"   Video ID: {video_id}")
        print(f"   URL: {video_url}")

        return UploadResult(
            video_id=video_id,
            video_url=video_url,
            title=title or video_path.stem,
            privacy_status=privacy,
            uploaded_at=datetime.now().isoformat(),
            file_path=str(video_path),
            platform="facebook",
        )

    def upload_batch_facebook(
        self,
        video_paths: List[Path],
        title_template: str = "{filename} - Part {n}",
        description: str = "",
        tags: Optional[List[str]] = None,
        privacy: str = "public",
    ) -> List[UploadResult]:
        """Upload multiple videos as Facebook Reels.

        Template placeholders:
          {n}: chunk number (001, 002, ...)
          {filename}: base filename without extension
          {total}: total number of videos

        Args:
            video_paths: List of video file paths.
            title_template: Title template with placeholders.
            description: Caption/description for all videos.
            tags: Hashtag list (without #).
            privacy: "public", "friends", or "only_me".

        Returns:
            List of UploadResult objects (continues on per-video errors).
        """
        results = []
        total = len(video_paths)

        print(f"\n📘 Starting Facebook Reels batch upload: {total} video(s)\n")

        for i, video_path in enumerate(video_paths, start=1):
            filename = video_path.stem.replace("_facebook_reels", "")
            import re
            chunk_match = re.search(r'_chunk_(\d+)', video_path.stem)
            chunk_num = int(chunk_match.group(1)) if chunk_match else i
            title = title_template.format(
                n=str(chunk_num).zfill(3), filename=filename, total=total
            )

            try:
                result = self.upload_facebook_reel(
                    video_path=video_path,
                    title=title,
                    description=description,
                    tags=tags,
                    privacy=privacy,
                )
                results.append(result)
                print()
            except Exception as e:
                print(f"❌ Facebook upload failed: {video_path.name}")
                print(f"   Error: {e}\n")

        print(f"✅ Facebook batch upload complete: {len(results)}/{total} successful\n")
        return results

    # ------------------------------------------------------------------
    # Instagram Reels
    # ------------------------------------------------------------------

    def _upload_to_catbox(self, video_path: Path) -> str:
        """Upload video to catbox.moe and return public URL.

        catbox.moe is a free file host (200 MB limit) used as a relay
        because Instagram's rupload.facebook.com binary upload returns 404
        for accounts without established Reels API eligibility.

        Args:
            video_path: Path to video file.

        Returns:
            Public HTTPS URL of the uploaded file.

        Raises:
            RuntimeError: If the upload fails.
        """
        file_size = video_path.stat().st_size
        if file_size > 200 * 1024 * 1024:
            raise RuntimeError(
                f"Video file too large for Instagram upload relay "
                f"({file_size / 1024 / 1024:.0f} MB, max 200 MB)"
            )

        print(f"   Uploading to temporary host (catbox.moe)...")
        with open(video_path, "rb") as f:
            resp = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": (video_path.name, f, "video/mp4")},
                timeout=300,
            )
        if not resp.ok or "files.catbox.moe" not in resp.text.strip():
            raise RuntimeError(
                f"Failed to upload to catbox.moe: {resp.text[:200]}"
            )
        url = resp.text.strip()
        print(f"   Temporary URL: {url}")
        return url

    def upload_instagram_reel(
        self,
        video_path: Path,
        caption: str = "",
    ) -> UploadResult:
        """Upload a single video as an Instagram Reel.

        Flow:
          1. Upload video to catbox.moe → get public URL
          2. POST /{ig_user_id}/media?media_type=REELS&video_url=...
             → id (container)
          3. Poll GET /{container_id}?fields=status_code until FINISHED
          4. POST /{ig_user_id}/media_publish?creation_id={container_id}

        Args:
            video_path: Path to video file.
            caption: Caption text (can include hashtags).

        Returns:
            UploadResult with media ID and URL.

        Raises:
            FileNotFoundError: If video file doesn't exist.
            RuntimeError: On API, upload, or status check errors.
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if not self.ig_user_id:
            raise ValueError(
                "META_IG_USER_ID not set in ~/.trendwatch/.env (required for --u-ig)"
            )

        file_size = video_path.stat().st_size

        print(f"📤 Uploading Instagram Reel: {video_path.name}")
        print(f"   File: {video_path.name}  ({file_size / 1024 / 1024:.1f} MB)")

        # ── Step 1: Upload to temporary public host ───────────────────
        public_video_url = self._upload_to_catbox(video_path)

        # ── Step 2: Create media container with video_url ─────────────
        container_resp = requests.post(
            f"{GRAPH_API_BASE}/{self.ig_user_id}/media",
            params={
                "media_type": "REELS",
                "video_url": public_video_url,
                "caption": caption[:2200] if caption else "",
                "share_to_feed": "true",
                "access_token": self.access_token,
            },
            timeout=30,
        )
        self._raise_for_graph_error(container_resp, "create IG media container")

        container_id = container_resp.json()["id"]

        print("   Container created, waiting for processing...")

        # ── Step 3: Poll for status ───────────────────────────────────
        status_code = None
        for attempt in range(MAX_POLL_ATTEMPTS):
            time.sleep(POLL_INTERVAL)
            status_resp = requests.get(
                f"{GRAPH_API_BASE}/{container_id}",
                params={
                    "fields": "status_code,status",
                    "access_token": self.access_token,
                },
                timeout=30,
            )
            self._raise_for_graph_error(status_resp, "check IG container status")

            status_data = status_resp.json()
            status_code = status_data.get("status_code", "")

            if status_code == "FINISHED":
                break
            elif status_code == "ERROR":
                error_msg = status_data.get("status", "Unknown error")
                raise RuntimeError(f"Instagram video processing failed: {error_msg}")
            elif status_code == "EXPIRED":
                raise RuntimeError("Instagram media container expired before publishing.")

            print(f"   Status: {status_code} (attempt {attempt + 1}/{MAX_POLL_ATTEMPTS})")

        if status_code != "FINISHED":
            raise RuntimeError(
                f"Instagram video did not finish processing after "
                f"{MAX_POLL_ATTEMPTS * POLL_INTERVAL}s (last status: {status_code})"
            )

        # ── Step 4: Publish ───────────────────────────────────────────
        publish_resp = requests.post(
            f"{GRAPH_API_BASE}/{self.ig_user_id}/media_publish",
            params={
                "creation_id": container_id,
                "access_token": self.access_token,
            },
            timeout=30,
        )
        self._raise_for_graph_error(publish_resp, "publish IG reel")

        published_id = publish_resp.json()["id"]
        video_url = f"https://www.instagram.com/reel/{published_id}/"

        print(f"✅ Instagram Reel published!")
        print(f"   Media ID: {published_id}")
        print(f"   URL: {video_url}")

        return UploadResult(
            video_id=published_id,
            video_url=video_url,
            title=caption[:80] if caption else video_path.stem,
            privacy_status="public",  # Instagram Reels are always public
            uploaded_at=datetime.now().isoformat(),
            file_path=str(video_path),
            platform="instagram",
        )

    def upload_batch_instagram(
        self,
        video_paths: List[Path],
        caption_template: str = "{filename} - Part {n}",
    ) -> List[UploadResult]:
        """Upload multiple videos as Instagram Reels.

        Template placeholders:
          {n}: chunk number (001, 002, ...)
          {filename}: base filename without extension
          {total}: total number of videos

        Args:
            video_paths: List of video file paths.
            caption_template: Caption template with placeholders.

        Returns:
            List of UploadResult objects (continues on per-video errors).
        """
        results = []
        total = len(video_paths)

        print(f"\n📷 Starting Instagram Reels batch upload: {total} video(s)\n")

        for i, video_path in enumerate(video_paths, start=1):
            filename = video_path.stem.replace("_instagram_reels", "")
            import re
            chunk_match = re.search(r'_chunk_(\d+)', video_path.stem)
            chunk_num = int(chunk_match.group(1)) if chunk_match else i
            caption = caption_template.format(
                n=str(chunk_num).zfill(3), filename=filename, total=total
            )

            try:
                result = self.upload_instagram_reel(
                    video_path=video_path,
                    caption=caption,
                )
                results.append(result)
                print()
            except Exception as e:
                print(f"❌ Instagram upload failed: {video_path.name}")
                print(f"   Error: {e}\n")

        print(f"✅ Instagram batch upload complete: {len(results)}/{total} successful\n")
        return results

    # ------------------------------------------------------------------
    # Metadata persistence
    # ------------------------------------------------------------------

    def save_upload_metadata(self, results: List[UploadResult], output_path: Path):
        """Save upload results to a JSON file.

        Args:
            results: List of UploadResult objects.
            output_path: Path to write the JSON file.
        """
        metadata = {
            "uploaded_at": datetime.now().isoformat(),
            "total_uploads": len(results),
            "videos": [asdict(r) for r in results],
        }

        with open(output_path, "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"💾 Upload metadata saved: {output_path}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _raise_for_graph_error(response: requests.Response, context: str):
        """Raise RuntimeError with a readable message if the Graph API returned an error.

        Args:
            response: The requests.Response object.
            context: Short description of the API call (for error messages).
        """
        try:
            data = response.json()
        except Exception:
            response.raise_for_status()
            return

        if "error" in data:
            err = data["error"]
            raise RuntimeError(
                f"Meta API error during {context}: "
                f"[{err.get('code')}] {err.get('message', err)}"
            )

        if not response.ok:
            raise RuntimeError(
                f"HTTP {response.status_code} during {context}: {response.text[:200]}"
            )
