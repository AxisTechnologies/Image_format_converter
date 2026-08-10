import os
import time
import logging
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger("PNG2JPEG.Watcher")

def wait_for_file_stability(
    file_path: str,
    max_retries: int = 10,
    check_interval: float = 0.5
) -> bool:
    """
    Checks if a file is done being copied/written by monitoring size stability
    and trying exclusive read-binary access.
    """
    if not os.path.exists(file_path):
        return False

    previous_size = -1
    for attempt in range(max_retries):
        try:
            current_size = os.path.getsize(file_path)
            # If size > 0 and unchanged since last iteration
            if current_size > 0 and current_size == previous_size:
                # Try opening file to verify exclusive/unlocked state
                with open(file_path, "rb") as f:
                    # Successfully opened, read first byte
                    f.read(1)
                return True
            previous_size = current_size
        except (PermissionError, OSError, IOError) as e:
            logger.debug(f"File lock check attempt {attempt + 1}/{max_retries} for {file_path}: {e}")
        
        time.sleep(check_interval)

    return False


class ImageFolderHandler(FileSystemEventHandler):
    """Watchdog event handler filtering for allowed image extensions and triggering stability check."""

    def __init__(self, callback: Callable[[str], None], allowed_exts: Optional[list] = None, include_subfolders: bool = False):
        super().__init__()
        self.callback = callback
        self.include_subfolders = include_subfolders
        self.allowed_exts = [e.lower() for e in (allowed_exts or [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".avif"])]

    def _process_event(self, event):
        if event.is_directory:
            return
        
        filepath = event.src_path
        ext = os.path.splitext(filepath)[1].lower()
        if ext in self.allowed_exts:
            if wait_for_file_stability(filepath):
                self.callback(filepath)
            else:
                logger.warning(f"File stability check failed for: {filepath}")

    def on_created(self, event):
        self._process_event(event)

    def on_modified(self, event):
        self._process_event(event)


class FolderWatcherService:
    """Manages Watchdog Observer lifecycle for the source directory."""

    def __init__(self, on_png_detected: Callable[[str], None]):
        self.on_png_detected = on_png_detected
        self.observer: Optional[Observer] = None
        self.is_monitoring: bool = False
        self.current_folder: str = ""

    def start_monitoring(self, folder_path: str, allowed_exts: Optional[list] = None, include_subfolders: bool = False) -> bool:
        """Starts monitoring the target directory."""
        self.stop_monitoring()

        if not folder_path or not os.path.exists(folder_path):
            logger.error(f"Cannot start watcher: Invalid folder path {folder_path}")
            return False

        try:
            self.handler = ImageFolderHandler(self.on_png_detected, allowed_exts=allowed_exts, include_subfolders=include_subfolders)
            self.observer = Observer()
            self.observer.schedule(self.handler, folder_path, recursive=include_subfolders)
            self.observer.start()
            self.is_monitoring = True
            self.current_folder = folder_path
            logger.info(f"Folder watcher started on: {folder_path} (recursive={include_subfolders})")
            return True
        except Exception as e:
            logger.error(f"Failed to start folder observer: {e}")
            self.is_monitoring = False
            return False

    def stop_monitoring(self):
        """Stops the current observer if running."""
        if self.observer and self.observer.is_alive():
            try:
                self.observer.stop()
                self.observer.join(timeout=2.0)
                logger.info("Folder watcher stopped.")
            except Exception as e:
                logger.error(f"Error stopping watcher: {e}")
        self.observer = None
        self.is_monitoring = False
