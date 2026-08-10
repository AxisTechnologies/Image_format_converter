import os
import sys
import unittest
import tempfile
from PIL import Image

from image_converter import ImageConverter
from config_manager import ConfigManager
from processed_tracker import ProcessedTracker

class TestPNGConverterCore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.source_dir = os.path.join(self.temp_dir.name, "source")
        self.output_dir = os.path.join(self.temp_dir.name, "output")
        os.makedirs(self.source_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_standard_png_conversion(self):
        # 1. Create test RGB PNG file
        src_png = os.path.join(self.source_dir, "photo001.png")
        img = Image.new("RGB", (400, 300), color=(255, 0, 0))
        img.save(src_png, format="PNG")

        dest_jpg = os.path.join(self.output_dir, "photo001.jpg")
        settings = {
            "jpeg_quality": 100,
            "resize_mode": "Original Size",
            "transparency_color": "White"
        }

        result_path = ImageConverter.convert_png_to_jpeg(src_png, dest_jpg, settings)
        self.assertTrue(os.path.exists(result_path))
        
        with Image.open(result_path) as res_img:
            self.assertEqual(res_img.format, "JPEG")
            self.assertEqual(res_img.size, (400, 300))

    def test_rgba_transparency_compositing(self):
        # Create transparent RGBA PNG file
        src_png = os.path.join(self.source_dir, "transparent.png")
        img = Image.new("RGBA", (200, 200), color=(0, 255, 0, 128))
        img.save(src_png, format="PNG")

        dest_jpg = os.path.join(self.output_dir, "transparent.jpg")
        settings = {
            "jpeg_quality": 90,
            "resize_mode": "Original Size",
            "transparency_color": "White"
        }

        result_path = ImageConverter.convert_png_to_jpeg(src_png, dest_jpg, settings)
        self.assertTrue(os.path.exists(result_path))

    def test_resizing_and_aspect_ratio(self):
        src_png = os.path.join(self.source_dir, "large.png")
        img = Image.new("RGB", (4000, 3000), color=(0, 0, 255))
        img.save(src_png, format="PNG")

        dest_jpg = os.path.join(self.output_dir, "large.jpg")
        settings = {
            "jpeg_quality": 100,
            "resize_mode": "Fixed Width",
            "custom_width": 2000,
            "maintain_aspect_ratio": True
        }

        result_path = ImageConverter.convert_png_to_jpeg(src_png, dest_jpg, settings)
        with Image.open(result_path) as res_img:
            self.assertEqual(res_img.size, (2000, 1500))

    def test_unicode_and_special_filenames(self):
        unicode_name = "भारत_мела (2026).png"
        src_png = os.path.join(self.source_dir, unicode_name)
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        img.save(src_png, format="PNG")

        dest_jpg = os.path.join(self.output_dir, "भारत_мела (2026).jpg")
        settings = {"jpeg_quality": 100, "resize_mode": "Original Size"}

        result_path = ImageConverter.convert_png_to_jpeg(src_png, dest_jpg, settings)
        self.assertTrue(os.path.exists(result_path))

    def test_processed_tracker(self):
        tracker = ProcessedTracker(self.temp_dir.name)
        src_png = os.path.join(self.source_dir, "tracked.png")
        img = Image.new("RGB", (50, 50))
        img.save(src_png, format="PNG")

        self.assertFalse(tracker.is_processed(src_png))
        tracker.mark_processed(src_png)
        self.assertTrue(tracker.is_processed(src_png))

if __name__ == "__main__":
    unittest.main()
