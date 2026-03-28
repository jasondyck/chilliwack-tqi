"""Download and extract GTFS feed from BC Transit."""

import hashlib
import io
import zipfile
from pathlib import Path

import requests

from tqi.config import GTFS_DIR, GTFS_URL

EXPECTED_FILES = ["stops.txt", "stop_times.txt", "trips.txt", "routes.txt"]


def download_gtfs(url: str = GTFS_URL, dest_dir: Path = GTFS_DIR) -> Path:
    """Download GTFS zip and extract to dest_dir. Returns extraction path."""
    dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading GTFS feed from {url} ...")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()

    # Save hash for cache invalidation
    feed_hash = hashlib.sha256(resp.content).hexdigest()
    (dest_dir / ".feed_hash").write_text(feed_hash)

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        zf.extractall(dest_dir)

    # Validate
    missing = [f for f in EXPECTED_FILES if not (dest_dir / f).exists()]
    if missing:
        raise FileNotFoundError(f"GTFS feed missing expected files: {missing}")

    print(f"GTFS extracted to {dest_dir}  ({len(list(dest_dir.glob('*.txt')))} files)")
    return dest_dir


def get_feed_hash(gtfs_dir: Path = GTFS_DIR) -> str | None:
    """Return the SHA-256 hash of the last downloaded feed, or None."""
    hash_file = gtfs_dir / ".feed_hash"
    if hash_file.exists():
        return hash_file.read_text().strip()
    return None
