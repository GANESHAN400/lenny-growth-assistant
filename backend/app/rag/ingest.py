"""Transcript ingestion script - downloads Lenny's podcast transcripts from GitHub.

The repo structure is:
  episodes/
    <guest-name>/
      transcript.md (or similar)
"""
import asyncio
import json
from pathlib import Path

import httpx
from loguru import logger

GITHUB_API_BASE = "https://api.github.com/repos/ChatPRD/lennys-podcast-transcripts/contents"
TRANSCRIPTS_DIR = Path(__file__).parent.parent.parent / "data" / "transcripts"

HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "lenny-growth-assistant/1.0",
}


async def fetch_json(client: httpx.AsyncClient, url: str) -> list | dict:
    """Fetch JSON from GitHub API."""
    response = await client.get(url, headers=HEADERS, timeout=30.0)
    response.raise_for_status()
    return response.json()


async def download_file(
    client: httpx.AsyncClient,
    download_url: str,
    output_path: Path,
) -> bool:
    """Download a file to output_path."""
    if output_path.exists() and output_path.stat().st_size > 100:
        return True  # Skip already downloaded
    try:
        response = await client.get(download_url, timeout=60.0, follow_redirects=True)
        response.raise_for_status()
        output_path.write_text(response.text, encoding="utf-8", errors="replace")
        return True
    except Exception as e:
        logger.debug(f"Download failed {download_url}: {e}")
        return False


async def process_episode_dir(
    client: httpx.AsyncClient,
    dir_url: str,
    episode_name: str,
    output_dir: Path,
) -> bool:
    """Process a single episode directory and download its transcript file(s)."""
    try:
        items = await fetch_json(client, dir_url)
        if not isinstance(items, list):
            return False

        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("name", "")
            item_type = item.get("type", "")
            download_url = item.get("download_url")

            # Find transcript files
            if item_type == "file" and download_url and (
                name.endswith(".md") or name.endswith(".txt")
            ):
                # Save as episode_name.md for easy identification
                safe_name = episode_name.replace("/", "_")
                output_path = output_dir / f"{safe_name}.md"
                if await download_file(client, download_url, output_path):
                    return True

        return False
    except Exception as e:
        logger.debug(f"Error processing {episode_name}: {e}")
        return False


async def ingest_transcripts(
    output_dir: Path | None = None,
    max_episodes: int = 100,
) -> int:
    """Download Lenny podcast transcripts from GitHub. Returns count downloaded."""
    target_dir = output_dir or TRANSCRIPTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Fetching episode list from GitHub...")

    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            # Get root contents
            items = await fetch_json(client, GITHUB_API_BASE)
            if not isinstance(items, list):
                logger.error("Unexpected GitHub API response")
                return 0

            # Find the 'episodes' directory
            episodes_url = None
            for item in items:
                if isinstance(item, dict) and item.get("name") == "episodes" and item.get("type") == "dir":
                    episodes_url = item.get("url")
                    break

            if not episodes_url:
                logger.error("Could not find 'episodes' directory in repo")
                return 0

            # Get list of episode subdirectories
            episode_dirs = await fetch_json(client, episodes_url)
            if not isinstance(episode_dirs, list):
                return 0

            episode_dirs = [
                d for d in episode_dirs
                if isinstance(d, dict) and d.get("type") == "dir"
            ][:max_episodes]

            logger.info(f"Found {len(episode_dirs)} episode directories")

            downloaded = 0
            # Process in batches of 8
            batch_size = 8
            for i in range(0, len(episode_dirs), batch_size):
                batch = episode_dirs[i:i + batch_size]
                tasks = [
                    process_episode_dir(
                        client,
                        d["url"],
                        d["name"],
                        target_dir,
                    )
                    for d in batch
                    if d.get("url")
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if result is True:
                        downloaded += 1

                if downloaded % 20 == 0 and downloaded > 0:
                    logger.info(f"Progress: {downloaded} transcripts downloaded...")

            logger.info(
                f"Ingestion complete: {downloaded}/{len(episode_dirs)} episodes downloaded to {target_dir}"
            )
            return downloaded

        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            return 0


if __name__ == "__main__":
    count = asyncio.run(ingest_transcripts(max_episodes=150))
    print(f"Downloaded {count} transcripts")
