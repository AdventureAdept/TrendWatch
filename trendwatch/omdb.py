"""OMDb API integration for fetching movie/show metadata."""

import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class OMDbClient:
    """Client for OMDb API (Open Movie Database)."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize OMDb client.

        Args:
            api_key: OMDb API key. If not provided, will look for OMDB_API_KEY env var.

        Raises:
            ValueError: If no API key is provided or found in environment.
        """
        self.api_key = api_key or os.getenv("OMDB_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OMDb API key required. Set OMDB_API_KEY environment variable or pass api_key parameter.\n"
                "Get a free key at: http://www.omdbapi.com/apikey.aspx"
            )
        self.base_url = "http://www.omdbapi.com/"

    def extract_imdb_id(self, filename: str) -> Optional[str]:
        """Extract IMDb ID from filename.

        Args:
            filename: Video filename (e.g., "tt1234567.mp4" or "tt1234567_chunk_001.mp4")

        Returns:
            IMDb ID (e.g., "tt1234567") or None if not found

        Examples:
            >>> client = OMDbClient("fake_key")
            >>> client.extract_imdb_id("tt1234567.mp4")
            'tt1234567'
            >>> client.extract_imdb_id("/path/to/tt9999999_chunk_01.mp4")
            'tt9999999'
        """
        # Extract just the filename from full path
        basename = Path(filename).stem

        # Match IMDb ID pattern: tt followed by 7-8 digits
        match = re.search(r'(tt\d{7,8})', basename)
        if match:
            return match.group(1)

        logger.warning(f"Could not extract IMDb ID from filename: {filename}")
        return None

    def fetch_metadata(self, imdb_id: str) -> dict:
        """Fetch movie/show metadata from OMDb API.

        Args:
            imdb_id: IMDb ID (e.g., "tt1234567")

        Returns:
            Dictionary containing movie metadata

        Raises:
            requests.RequestException: If API request fails
            ValueError: If IMDb ID is invalid or movie not found
        """
        # Validate IMDb ID format
        if not re.match(r'tt\d{7,8}', imdb_id):
            raise ValueError(f"Invalid IMDb ID format: {imdb_id}")

        logger.info(f"Fetching metadata for IMDb ID: {imdb_id}")

        params = {
            "apikey": self.api_key,
            "i": imdb_id,  # IMDb ID
            "plot": "full",  # Get full plot summary
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("Response") == "False":
                error_msg = data.get("Error", "Unknown error")
                raise ValueError(f"OMDb API error for {imdb_id}: {error_msg}")

            logger.info(f"✅ Fetched metadata for: {data.get('Title', 'Unknown')}")
            return data

        except requests.RequestException as e:
            logger.error(f"Failed to fetch OMDb data: {e}")
            raise

    def save_metadata(self, metadata: dict, output_path: Path) -> None:
        """Save metadata to JSON file.

        Args:
            metadata: Movie metadata dictionary
            output_path: Path to save JSON file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 Saved metadata to: {output_path}")

    def fetch_and_save(self, video_path: Path, output_dir: Optional[Path] = None) -> Optional[Path]:
        """Extract IMDb ID from video filename, fetch metadata, and save to file.

        Args:
            video_path: Path to video file (filename should contain IMDb ID)
            output_dir: Directory to save metadata (default: same as video)

        Returns:
            Path to saved metadata file, or None if IMDb ID not found

        Example:
            >>> client = OMDbClient("your_api_key")
            >>> metadata_path = client.fetch_and_save(Path("tt1234567.mp4"))
            >>> # Creates tt1234567_metadata.json
        """
        # Extract IMDb ID from filename
        imdb_id = self.extract_imdb_id(video_path.name)
        if not imdb_id:
            logger.warning(f"Skipping OMDb fetch - no IMDb ID in filename: {video_path.name}")
            return None

        # Fetch metadata
        try:
            metadata = self.fetch_metadata(imdb_id)
        except (requests.RequestException, ValueError) as e:
            logger.error(f"Failed to fetch metadata for {imdb_id}: {e}")
            return None

        # Determine output path
        if output_dir is None:
            output_dir = video_path.parent

        output_path = output_dir / f"{imdb_id}_metadata.json"

        # Save to file
        self.save_metadata(metadata, output_path)
        return output_path

    def get_relevant_fields(self, metadata: dict) -> dict:
        """Extract only the relevant fields we need from full OMDb response.

        Args:
            metadata: Full OMDb API response

        Returns:
            Dictionary with only relevant fields
        """
        return {
            "imdb_id": metadata.get("imdbID"),
            "title": metadata.get("Title"),
            "year": metadata.get("Year"),
            "genre": metadata.get("Genre"),
            "director": metadata.get("Director"),
            "actors": metadata.get("Actors"),
            "plot": metadata.get("Plot"),
            "language": metadata.get("Language"),
            "country": metadata.get("Country"),
            "imdb_rating": metadata.get("imdbRating"),
            "runtime": metadata.get("Runtime"),
            "type": metadata.get("Type"),  # movie, series, episode
        }
