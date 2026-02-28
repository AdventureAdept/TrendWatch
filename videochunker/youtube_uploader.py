"""YouTube Data API v3 client for uploading Shorts videos.

This module provides OAuth 2.0 authentication with token caching and
batch upload functionality for YouTube Shorts, with automatic metadata
generation from IMDb data.
"""

import json
import os
import pickle
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload


# OAuth 2.0 scope for YouTube uploads (minimal permissions)
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

# Default config directory
CONFIG_DIR = Path.home() / '.trendwatch'
DEFAULT_CREDENTIALS_PATH = CONFIG_DIR / 'client_secrets.json'
TOKEN_CACHE_PATH = CONFIG_DIR / 'youtube_token.pickle'


@dataclass
class UploadResult:
    """Result from a single video upload."""
    video_id: str
    video_url: str
    title: str
    privacy_status: str
    uploaded_at: str
    file_path: str


def format_metadata_for_youtube(
    imdb_metadata: Dict,
    chunk_number: int,
    total_chunks: int,
    title_template: Optional[str] = None,
    description_override: Optional[str] = None
) -> Dict[str, Any]:
    """Format IMDb metadata for YouTube upload.

    Args:
        imdb_metadata: IMDb metadata dictionary from OMDb API
        chunk_number: Current chunk number (1-indexed)
        total_chunks: Total number of chunks
        title_template: Optional title template (uses default if None)
        description_override: Optional description override (uses IMDb plot if None)

    Returns:
        Dictionary with 'title', 'description', and 'tags' keys
    """
    # Extract metadata fields
    movie_title = imdb_metadata.get('Title', 'Video')
    year = imdb_metadata.get('Year', '')
    plot = imdb_metadata.get('Plot', '')
    genre = imdb_metadata.get('Genre', '')
    director = imdb_metadata.get('Director', '')
    actors = imdb_metadata.get('Actors', '')
    imdb_rating = imdb_metadata.get('imdbRating', '')

    # Generate title
    if title_template:
        # Use custom template
        title = title_template.format(
            n=str(chunk_number).zfill(3),
            filename=movie_title,
            total=total_chunks
        )
    else:
        # Default: "Movie Title (Year) - Part X"
        if year:
            title = f"{movie_title} ({year}) - Part {chunk_number}"
        else:
            title = f"{movie_title} - Part {chunk_number}"

    # Ensure title is within YouTube's 100 character limit
    if len(title) > 100:
        title = title[:97] + "..."

    # Generate description
    if description_override:
        description = description_override
    else:
        # Default: Use plot summary
        description_parts = []

        if plot and plot != 'N/A':
            description_parts.append(plot)

        if imdb_rating and imdb_rating != 'N/A':
            description_parts.append(f"\n⭐ IMDb Rating: {imdb_rating}/10")

        if director and director != 'N/A':
            description_parts.append(f"🎬 Director: {director}")

        description = "\n".join(description_parts) if description_parts else movie_title

    # Auto-add #Shorts tag
    if '#Shorts' not in description:
        description += "\n\n#Shorts"

    # Generate tags from metadata
    tags = []

    # Add genre tags
    if genre and genre != 'N/A':
        # Split genres and clean them
        genre_list = [g.strip().replace(' ', '') for g in genre.split(',')]
        tags.extend(genre_list[:3])  # Limit to 3 genres

    # Add actor tags (first 2 actors)
    if actors and actors != 'N/A':
        actor_list = [a.strip() for a in actors.split(',')]
        tags.extend(actor_list[:2])

    # Add standard tags
    tags.extend(['Shorts', 'MovieClips', movie_title.replace(' ', '')])

    # Add year if available
    if year and year != 'N/A':
        tags.append(year)

    # Remove duplicates and limit to 15 tags (YouTube limit is 500 chars total)
    seen = set()
    unique_tags = []
    for tag in tags:
        if tag and tag not in seen and len(tag) > 1:
            seen.add(tag)
            unique_tags.append(tag)
            if len(unique_tags) >= 15:
                break

    return {
        'title': title,
        'description': description,
        'tags': unique_tags
    }


class YouTubeUploader:
    """Client for uploading videos to YouTube using OAuth 2.0."""

    def __init__(self, credentials_path: Optional[Path] = None):
        """Initialize uploader with OAuth credentials.

        Args:
            credentials_path: Path to client_secrets.json file.
                            Defaults to ~/.trendwatch/client_secrets.json

        Raises:
            ValueError: If credentials file doesn't exist with setup instructions.
        """
        self.credentials_path = credentials_path or DEFAULT_CREDENTIALS_PATH

        if not self.credentials_path.exists():
            raise ValueError(
                "YouTube OAuth credentials not found.\n\n"
                "To enable YouTube uploads, follow these steps:\n\n"
                "1. Go to Google Cloud Console:\n"
                "   https://console.cloud.google.com/\n\n"
                "2. Create a new project or select existing project\n\n"
                "3. Enable YouTube Data API v3:\n"
                "   https://console.cloud.google.com/apis/library/youtube.googleapis.com\n\n"
                "4. Create OAuth 2.0 credentials:\n"
                "   - Go to Credentials → Create Credentials → OAuth client ID\n"
                "   - Application type: Desktop app\n"
                "   - Download the JSON file\n\n"
                f"5. Save credentials file to:\n"
                f"   {self.credentials_path}\n\n"
                "6. Run command again - browser will open for authorization\n"
            )

        self.youtube = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with YouTube API using OAuth 2.0.

        First-time: Opens browser for authorization and caches token.
        Subsequent: Loads cached token, auto-refreshes if expired.
        """
        creds = None

        # Load cached token if exists
        if TOKEN_CACHE_PATH.exists():
            with open(TOKEN_CACHE_PATH, 'rb') as token:
                creds = pickle.load(token)

        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Refresh expired token
                print("🔄 Refreshing YouTube authentication token...")
                creds.refresh(Request())
            else:
                # New authentication flow
                print("🌐 Opening browser for YouTube authentication...")
                print("   (You'll need to authorize this app to upload videos)")

                # Ensure config directory exists
                CONFIG_DIR.mkdir(parents=True, exist_ok=True)

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path),
                    SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save token for future use
            with open(TOKEN_CACHE_PATH, 'wb') as token:
                pickle.dump(creds, token)
            print("✅ Authentication successful! Token cached for future use.")

        # Build YouTube API client
        self.youtube = build('youtube', 'v3', credentials=creds)

    def upload_short(
        self,
        video_path: Path,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        privacy_status: str = "public"
    ) -> UploadResult:
        """Upload a single video to YouTube as a Short.

        Args:
            video_path: Path to video file
            title: Video title (max 100 chars recommended)
            description: Video description (auto-adds #Shorts tag)
            tags: List of tags for the video
            privacy_status: "public", "unlisted", or "private"

        Returns:
            UploadResult with video ID, URL, and metadata

        Raises:
            HttpError: On API errors (quota exceeded, network failure, etc.)
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Add #Shorts tag to description if not present
        if description and '#Shorts' not in description:
            description = f"{description}\n\n#Shorts"
        elif not description:
            description = "#Shorts"

        # Prepare video metadata
        body = {
            'snippet': {
                'title': title[:100],  # YouTube title limit
                'description': description,
                'tags': tags or [],
                'categoryId': '22'  # People & Blogs (standard for Shorts)
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False
            }
        }

        # Prepare resumable upload with 1MB chunks
        media = MediaFileUpload(
            str(video_path),
            chunksize=1024 * 1024,  # 1MB chunks
            resumable=True
        )

        print(f"📤 Uploading: {title}")
        print(f"   File: {video_path.name}")

        # Execute upload
        request = self.youtube.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media
        )

        response = None
        last_progress = 0

        while response is None:
            status, response = request.next_chunk()
            if status:
                # Log progress at 25% intervals
                progress = int(status.progress() * 100)
                if progress >= last_progress + 25:
                    print(f"   Progress: {progress}%")
                    last_progress = progress

        video_id = response['id']
        video_url = f"https://youtube.com/shorts/{video_id}"

        print(f"✅ Upload complete!")
        print(f"   Video ID: {video_id}")
        print(f"   URL: {video_url}")

        return UploadResult(
            video_id=video_id,
            video_url=video_url,
            title=title,
            privacy_status=privacy_status,
            uploaded_at=datetime.now().isoformat(),
            file_path=str(video_path)
        )

    def upload_batch(
        self,
        video_paths: List[Path],
        title_template: str = "{filename} - Part {n}",
        description: str = "",
        tags: Optional[List[str]] = None,
        privacy_status: str = "public"
    ) -> List[UploadResult]:
        """Upload multiple videos with templated titles.

        Template placeholders:
        - {n}: Chunk number (001, 002, ...)
        - {filename}: Base filename without extension
        - {total}: Total number of videos

        Args:
            video_paths: List of video file paths to upload
            title_template: Title template with placeholders
            description: Description for all videos (auto-adds #Shorts)
            tags: List of tags for all videos
            privacy_status: "public", "unlisted", or "private"

        Returns:
            List of UploadResult objects (continues on errors)
        """
        results = []
        total = len(video_paths)

        print(f"\n📺 Starting batch upload: {total} video(s)\n")

        for i, video_path in enumerate(video_paths, start=1):
            # Extract filename without extension
            filename = video_path.stem.replace('_youtube_shorts', '')

            # Format title with template
            title = title_template.format(
                n=str(i).zfill(3),
                filename=filename,
                total=total
            )

            try:
                result = self.upload_short(
                    video_path=video_path,
                    title=title,
                    description=description,
                    tags=tags,
                    privacy_status=privacy_status
                )
                results.append(result)
                print()  # Blank line between uploads

            except HttpError as e:
                # Handle quota exceeded
                if e.resp.status == 403 and 'quotaExceeded' in str(e):
                    print(f"\n❌ YouTube API quota exceeded!")
                    print(f"   Daily limit: 10,000 units (~6 uploads)")
                    print(f"   Resets: Midnight Pacific Time")
                    print(f"   Request increase: https://console.cloud.google.com/iam-admin/quotas")
                    print(f"\n   Successfully uploaded {len(results)}/{total} videos before quota limit.")
                    break
                else:
                    print(f"❌ Upload failed: {video_path.name}")
                    print(f"   Error: {e}")
                    print()
                    # Continue with next video

            except Exception as e:
                print(f"❌ Upload failed: {video_path.name}")
                print(f"   Error: {e}")
                print()
                # Continue with next video

        print(f"✅ Batch upload complete: {len(results)}/{total} successful\n")
        return results

    def save_upload_metadata(self, results: List[UploadResult], output_path: Path):
        """Save upload results to JSON file.

        Args:
            results: List of UploadResult objects
            output_path: Path to save JSON file
        """
        metadata = {
            'uploaded_at': datetime.now().isoformat(),
            'total_uploads': len(results),
            'videos': [asdict(result) for result in results]
        }

        with open(output_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"💾 Upload metadata saved: {output_path}")
