import os
import logging
from PIL import Image, ImageOps
from typing import Dict, Any, Tuple

logger = logging.getLogger("PNG2JPEG.Converter")

HEX_COLORS = {
    "White": "#FFFFFF",
    "Black": "#000000"
}

def parse_hex_color(color_str: str) -> Tuple[int, int, int]:
    """Converts a hex string like '#FFFFFF' or color name to an RGB tuple."""
    color_str = color_str.strip()
    if color_str in HEX_COLORS:
        color_str = HEX_COLORS[color_str]
    
    if color_str.startswith("#"):
        color_str = color_str[1:]
    
    if len(color_str) == 6:
        try:
            return (
                int(color_str[0:2], 16),
                int(color_str[2:4], 16),
                int(color_str[4:6], 16)
            )
        except ValueError:
            pass
    return (255, 255, 255)  # Default White

class ImageConverter:
    """Core image conversion engine handling PNG -> JPEG transformation, quality settings, transparency, and scaling."""

    @staticmethod
    def calculate_dimensions(
        orig_w: int,
        orig_h: int,
        mode: str,
        percent: int = 100,
        custom_w: int = 1920,
        custom_h: int = 1080,
        maintain_aspect: bool = True
    ) -> Tuple[int, int]:
        """Computes target (width, height) based on sizing mode and constraints."""
        if mode == "Original Size":
            return orig_w, orig_h
        
        elif mode == "Percentage":
            scale = max(1, percent) / 100.0
            return max(1, int(orig_w * scale)), max(1, int(orig_h * scale))
        
        elif mode == "Fixed Width":
            target_w = max(1, custom_w)
            if maintain_aspect:
                target_h = max(1, int(orig_h * (target_w / float(orig_w))))
            else:
                target_h = orig_h
            return target_w, target_h
        
        elif mode == "Fixed Width x Height":
            if not maintain_aspect:
                return max(1, custom_w), max(1, custom_h)
            else:
                # Scale to fit within custom_w x custom_h maintaining aspect ratio
                ratio = min(custom_w / float(orig_w), custom_h / float(orig_h))
                return max(1, int(orig_w * ratio)), max(1, int(orig_h * ratio))
        
        elif mode == "Max Width / Height":
            if orig_w <= custom_w and orig_h <= custom_h:
                return orig_w, orig_h
            ratio = min(custom_w / float(orig_w), custom_h / float(orig_h))
            return max(1, int(orig_w * ratio)), max(1, int(orig_h * ratio))
        
        return orig_w, orig_h

    @staticmethod
    def convert_image(
        source_path: str,
        output_path: str,
        settings: Dict[str, Any]
    ) -> str:
        """
        Converts a single input image (PNG, WebP, AVIF, BMP, TIFF, JPEG) to target output format
        (JPEG, PNG, WEBP, AVIF, BMP) using configuration settings.
        Returns the output destination file path upon success.
        """
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source file does not exist: {source_path}")

        # Ensure output directory exists
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        target_fmt = settings.get("target_output_format", "JPEG").upper()
        if target_fmt in ("JPG", "JPEG"):
            pil_format = "JPEG"
        elif target_fmt == "PNG":
            pil_format = "PNG"
        elif target_fmt == "WEBP":
            pil_format = "WEBP"
        elif target_fmt == "AVIF":
            pil_format = "AVIF"
        elif target_fmt == "BMP":
            pil_format = "BMP"
        else:
            pil_format = "JPEG"

        with Image.open(source_path) as img:
            # 1. Handle Transparency & Alpha Channels
            requires_rgb = pil_format in ("JPEG", "BMP")
            has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)

            if requires_rgb and has_alpha:
                rgba_img = img.convert("RGBA")
                bg_setting = settings.get("transparency_color", "White")
                hex_val = settings.get("custom_color_hex", "#FFFFFF") if bg_setting == "Custom" else HEX_COLORS.get(bg_setting, "#FFFFFF")
                bg_color = parse_hex_color(hex_val)
                bg_canvas = Image.new("RGB", rgba_img.size, bg_color)
                bg_canvas.paste(rgba_img, mask=rgba_img.split()[3])
                proc_img = bg_canvas
            elif requires_rgb:
                proc_img = img.convert("RGB")
            else:
                proc_img = img.copy()

            # 2. Handle Resizing
            orig_w, orig_h = proc_img.size
            target_w, target_h = ImageConverter.calculate_dimensions(
                orig_w, orig_h,
                mode=settings.get("resize_mode", "Original Size"),
                percent=settings.get("resize_percent", 100),
                custom_w=settings.get("custom_width", 1920),
                custom_h=settings.get("custom_height", 1080),
                maintain_aspect=settings.get("maintain_aspect_ratio", True)
            )

            if (target_w, target_h) != (orig_w, orig_h):
                proc_img = proc_img.resize((target_w, target_h), Image.Resampling.LANCZOS)

            # 3. Format Specific Encoding & Quality Options
            quality = int(settings.get("jpeg_quality", 100))
            quality = max(1, min(100, quality))

            save_kwargs = {"format": pil_format}

            if pil_format == "JPEG":
                save_kwargs.update({"quality": quality, "optimize": True})
                if quality == 100:
                    save_kwargs["subsampling"] = 0
                elif quality >= 85:
                    save_kwargs["subsampling"] = 1
                else:
                    save_kwargs["subsampling"] = 2
            elif pil_format == "WEBP":
                save_kwargs.update({"quality": quality, "method": 6})
            elif pil_format == "AVIF":
                save_kwargs.update({"quality": quality})
            elif pil_format == "PNG":
                save_kwargs.update({"optimize": True})

            icc_profile = img.info.get("icc_profile")
            if icc_profile and pil_format in ("JPEG", "PNG", "WEBP"):
                save_kwargs["icc_profile"] = icc_profile

            proc_img.save(output_path, **save_kwargs)
            logger.info(f"Successfully converted: {source_path} -> {output_path} ({pil_format}, Quality: {quality}%, Size: {target_w}x{target_h})")
            return output_path

    @staticmethod
    def convert_png_to_jpeg(source_path: str, output_path: str, settings: Dict[str, Any]) -> str:
        """Backward compatibility wrapper."""
        s = dict(settings)
        s["target_output_format"] = "JPEG"
        return ImageConverter.convert_image(source_path, output_path, s)
