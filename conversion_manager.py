import os
import re
import queue
import logging
import threading
from typing import Dict, Any, Optional, Tuple
from PySide6.QtCore import QObject, Signal

from image_converter import ImageConverter
from processed_tracker import ProcessedTracker
from folder_watcher import wait_for_file_stability

logger = logging.getLogger("PNG2JPEG.Manager")

class ConversionManager(QObject):
    """
    Coordinates conversion queue, background worker threads, collision policies,
    and updates stats signals for PySide6 UI.
    """
    
    # PySide6 Signals
    conversion_started = Signal(str)  # source_path
    conversion_success = Signal(str, str)  # source_path, output_path
    conversion_skipped = Signal(str, str)  # source_path, reason
    conversion_failed = Signal(str, str)   # source_path, error_msg
    stats_updated = Signal(dict)  # {"processed": X, "success": Y, "skipped": Z, "failed": W}

    def __init__(self, tracker: ProcessedTracker):
        super().__init__()
        self.tracker = tracker
        self.settings: Dict[str, Any] = {}
        self.work_queue: queue.Queue = queue.Queue()
        self.worker_thread: Optional[threading.Thread] = None
        self.is_running: bool = False
        self.enqueued_paths: set = set()
        
        # Stats counters
        self.stats = {
            "processed": 0,
            "success": 0,
            "skipped": 0,
            "failed": 0
        }

    def update_settings(self, new_settings: Dict[str, Any]):
        self.settings = dict(new_settings)

    def start(self):
        """Starts worker thread."""
        if not self.is_running:
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            logger.info("ConversionManager worker thread started.")

    def stop(self):
        """Stops worker thread."""
        self.is_running = False
        self.enqueued_paths.clear()
        # Push None to unblock queue get
        self.work_queue.put(None)

    def should_process_file(self, source_path: str) -> bool:
        """Determines if a source file needs processing (missing output or new/modified source file)."""
        if not source_path or not os.path.exists(source_path):
            return False
        out_path, _ = self.determine_output_path(source_path)
        # If output converted file is missing from destination folder, MUST process!
        if not os.path.exists(out_path):
            return True
        # If output file exists, process only if source image is new or modified
        return not self.tracker.is_processed(source_path)

    def enqueue_file(self, source_path: str, force: bool = False):
        """Pushes a file into conversion processing queue."""
        if not self.is_running or not source_path:
            return
        
        if not force and not self.should_process_file(source_path):
            return

        norm_p = os.path.normpath(source_path).lower()
        if norm_p in self.enqueued_paths:
            return
        
        self.enqueued_paths.add(norm_p)
        self.work_queue.put(source_path)

    def _worker_loop(self):
        while self.is_running:
            try:
                item = self.work_queue.get(timeout=1.0)
                if item is None:
                    break
                norm_p = os.path.normpath(item).lower()
                self.process_single_file(item)
                self.enqueued_paths.discard(norm_p)
                self.work_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")

    def determine_output_path(self, source_path: str) -> Tuple[str, str]:
        """
        Calculates output destination path based on target format settings
        and handles file collision policies.
        """
        source_dir = self.settings.get("source_folder", "")
        output_dir = self.settings.get("output_folder", "")
        policy = self.settings.get("existing_file_policy", "Skip")
        preserve_subfolders = self.settings.get("preserve_subfolder_structure", True)
        
        target_fmt = self.settings.get("target_output_format", "JPEG").lower()
        if target_fmt in ("jpeg", "jpg"):
            ext = ".jpg"
        else:
            ext = f".{target_fmt}"

        base_name = os.path.splitext(os.path.basename(source_path))[0]
        
        is_subfile = False
        rel_path = ""
        if source_dir:
            try:
                rel_path = os.path.relpath(source_path, source_dir)
                norm_rel = os.path.normpath(rel_path)
                is_subfile = not norm_rel.startswith("..") and not os.path.isabs(norm_rel)
            except ValueError:
                is_subfile = False

        if preserve_subfolders and is_subfile and rel_path != os.path.basename(source_path):
            rel_dir = os.path.dirname(rel_path)
            target_out_dir = os.path.normpath(os.path.join(output_dir, rel_dir))
        else:
            target_out_dir = os.path.normpath(output_dir)

        dest_file = os.path.join(target_out_dir, f"{base_name}{ext}")

        # Collision Handling
        if os.path.exists(dest_file):
            if policy == "Skip":
                return dest_file, "skip"
            elif policy == "Replace":
                return dest_file, "replace"
            elif policy == "Create Numbered Copy":
                count = 1
                while True:
                    candidate = os.path.join(target_out_dir, f"{base_name}_{count}{ext}")
                    if not os.path.exists(candidate):
                        return candidate, "create_numbered"
                    count += 1

        return dest_file, "convert"

    def process_single_file(self, source_path: str):
        """Processes a single image conversion task."""
        allowed = [e.lower() for e in self.settings.get("allowed_input_extensions", [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".avif"])]
        ext = os.path.splitext(source_path)[1].lower()

        if not source_path or ext not in allowed:
            return

        # Ensure file isn't located inside output destination directory
        out_dir = self.settings.get("output_folder", "")
        if out_dir:
            norm_src = os.path.normpath(source_path).lower()
            norm_out = os.path.normpath(out_dir).lower()
            if norm_src.startswith(norm_out + os.sep) or norm_src == norm_out:
                return

        # Wait for file write/copy to stabilize in worker thread
        if not wait_for_file_stability(source_path):
            logger.warning(f"File stability check failed for: {source_path}")
            return

        out_path, action = self.determine_output_path(source_path)
        
        if action == "skip":
            if not self.tracker.is_processed(source_path):
                logger.info(f"Skipping existing output file: {out_path}")
                self.stats["skipped"] += 1
                self.stats["processed"] += 1
                self.conversion_skipped.emit(source_path, "Output image file already exists in destination folder")
                self.stats_updated.emit(self.stats)
                self.tracker.mark_processed(source_path)
            return

        self.conversion_started.emit(source_path)

        try:
            res_path = ImageConverter.convert_image(source_path, out_path, self.settings)
            self.stats["success"] += 1
            self.stats["processed"] += 1
            self.conversion_success.emit(source_path, res_path)
            self.tracker.mark_processed(source_path)
        except Exception as e:
            err_msg = str(e)
            logger.error(f"Failed converting {source_path}: {err_msg}")
            self.stats["failed"] += 1
            self.stats["processed"] += 1
            self.conversion_failed.emit(source_path, err_msg)
            self.tracker.mark_processed(source_path)
            
        self.stats_updated.emit(self.stats)

    def scan_folder_and_enqueue(self, folder_path: str, recursive: bool = False, force: bool = False):
        """Scans folder for existing supported images and pushes un-processed or missing ones to queue."""
        if not folder_path or not os.path.exists(folder_path):
            return

        allowed = [e.lower() for e in self.settings.get("allowed_input_extensions", [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".avif"])]
        logger.info(f"Scanning folder for existing images: {folder_path} (recursive={recursive})")
        if recursive:
            for root, _, files in os.walk(folder_path):
                for f in files:
                    full_p = os.path.join(root, f)
                    if os.path.splitext(f)[1].lower() in allowed:
                        if force or self.should_process_file(full_p):
                            self.enqueue_file(full_p, force=force)
        else:
            try:
                for item in os.listdir(folder_path):
                    full_p = os.path.join(folder_path, item)
                    if os.path.isfile(full_p) and os.path.splitext(item)[1].lower() in allowed:
                        if force or self.should_process_file(full_p):
                            self.enqueue_file(full_p, force=force)
            except Exception as e:
                logger.error(f"Error scanning folder {folder_path}: {e}")
