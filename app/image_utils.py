"""Image validation, background removal, and paste fallback helpers."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageFilter
from rembg import remove


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def validate_upload(filename: str, content_type: str | None, data: bytes) -> None:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS or content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Only JPG and PNG image files are supported.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("Image must be 10 MB or smaller.")
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
    except Exception as exc:
        raise ValueError("The uploaded file is not a valid image.") from exc


def remove_background(data: bytes) -> bytes:
    return bytes(remove(data))


def create_fallback_composite(
    model_path: Path,
    jewelry_path: Path,
    position: dict[str, float],
    scale: float,
) -> bytes:
    with Image.open(model_path).convert("RGBA") as model, Image.open(
        jewelry_path
    ).convert("RGBA") as jewelry:
        target_width = max(1, int(model.width * scale))
        target_height = max(1, int(jewelry.height * target_width / jewelry.width))
        jewelry = jewelry.resize((target_width, target_height), Image.Resampling.LANCZOS)

        center_x = int(model.width * position["x"])
        center_y = int(model.height * position["y"])
        left = center_x - jewelry.width // 2
        top = center_y - jewelry.height // 2

        alpha = jewelry.getchannel("A")
        shadow = Image.new("RGBA", jewelry.size, (0, 0, 0, 0))
        shadow.putalpha(alpha.filter(ImageFilter.GaussianBlur(radius=6)).point(lambda p: p // 3))
        model.alpha_composite(shadow, (left + 4, top + 6))
        model.alpha_composite(jewelry, (left, top))

        output = io.BytesIO()
        model.convert("RGB").save(output, format="PNG")
        return output.getvalue()
