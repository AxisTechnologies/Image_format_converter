import os
import json
import logging
from typing import Set, Tuple

logger = logging.getLogger("PNG2JPEG.Tracker")

class ProcessedTracker:
    """
    Tracks processed PNG files using (file_path, size, mtime) tuples to prevent duplicate processing.
    Persists history to tracker_history.json in APPDATA directory.
    """

    def __init__(self, config_dir: str):
        self.tracker_file = os.path.join(config_dir, "tracker_history.json")
        # Stores keys formatted as: "normpath|size|mtime"
        self.processed_records: Set[str] = set()
        self.load()

    def _make_key(self, file_path: str, size: int, mtime: float) -> str:
        norm_path = os.path.normpath(file_path).lower()
        return f"{norm_path}|{size}|{int(mtime)}"

    def load(self):
        if os.path.exists(self.tracker_file):
            try:
                with open(self.tracker_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.processed_records = set(data)
                logger.info(f"Loaded {len(self.processed_records)} processed records.")
            except Exception as e:
                logger.error(f"Error loading processed tracker: {e}")
                self.processed_records = set()

    def save(self):
        try:
            with open(self.tracker_file, "w", encoding="utf-8") as f:
                json.dump(list(self.processed_records), f)
        except Exception as e:
            logger.error(f"Failed to save processed tracker: {e}")

    def is_processed(self, file_path: str) -> bool:
        if not os.path.exists(file_path):
            return False
        try:
            stat = os.stat(file_path)
            key = self._make_key(file_path, stat.st_size, stat.st_mtime)
            return key in self.processed_records
        except OSError:
            return False

    def mark_processed(self, file_path: str):
        if not os.path.exists(file_path):
            return
        try:
            stat = os.stat(file_path)
            key = self._make_key(file_path, stat.st_size, stat.st_mtime)
            self.processed_records.add(key)
            self.save()
        except OSError as e:
            logger.error(f"Failed to mark file processed {file_path}: {e}")

    def clear(self):
        self.processed_records.clear()
        self.save()
