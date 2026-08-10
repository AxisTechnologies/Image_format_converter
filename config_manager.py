import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger("PNG2JPEG.Config")

DEFAULT_CONFIG: Dict[str, Any] = {
    "source_folder": "",
    "output_folder": "",
    "target_output_format": "JPEG",  # "JPEG", "PNG", "WEBP", "AVIF", "BMP"
    "allowed_input_extensions": [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".avif"],
    "jpeg_quality": 100,
    "resize_mode": "Original Size",  # "Original Size", "Percentage", "Fixed Width", "Fixed Width x Height", "Max Width / Height"
    "resize_percent": 100,
    "custom_width": 1920,
    "custom_height": 1080,
    "maintain_aspect_ratio": True,
    "transparency_color": "White",  # "White", "Black", "Custom"
    "custom_color_hex": "#FFFFFF",
    "existing_file_policy": "Skip",  # "Skip", "Replace", "Create Numbered Copy"
    "process_existing_on_startup": True,
    "include_subfolders": False,
    "preserve_subfolder_structure": True,
    "start_with_windows": False,
    "start_minimized": False
}

class ConfigManager:
    """Manages application configuration persistence in %APPDATA%/PNG2JPEGConverter/settings.json"""
    
    def __init__(self):
        appdata_dir = os.environ.get("APPDATA", os.path.expanduser("~"))
        self.config_dir = os.path.join(appdata_dir, "PNG2JPEGConverter")
        os.makedirs(self.config_dir, exist_ok=True)
        self.config_file = os.path.join(self.config_dir, "settings.json")
        self.settings: Dict[str, Any] = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        """Loads configuration from JSON file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.settings.update(data)
                logger.info(f"Configuration loaded from {self.config_file}")
            except Exception as e:
                logger.error(f"Error loading configuration: {e}. Reverting to defaults.")
        else:
            self.save()

    def save(self):
        """Saves current configuration to JSON file."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
            logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def set(self, key: str, value: Any):
        self.settings[key] = value
        self.save()

    def update_dict(self, new_settings: Dict[str, Any]):
        self.settings.update(new_settings)
        self.save()
