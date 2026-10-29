"""Run a standalone low-quality JewelryTryOn image generation."""

from __future__ import annotations

import argparse
import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


PROMPT = (
    "Create a professional jewelry catalog try-on photo. "
    "The first image is the model; the second image is the jewelry product. "
    "Place the jewelry from the second image onto the model so it looks naturally worn: "
    "earrings on the earlobe, necklace around the neck, ring on a finger, or bracelet on the wrist. "
    "Preserve the jewelry design EXACTLY: same shape, metal color, stones, size proportions, and details. "
    "Keep the model's face, skin tone, pose, hair, and background unchanged. "
    "Match lighting and add soft realistic contact shadows and metal reflections on the skin. "
    "Photorealistic close-up lifestyle product photography, sharp jewelry focus, natural skin texture."
)
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a JewelryTryOn result from a model and jewelry image."
    )
    parser.add_argument("model_image", type=Path, help="Path to the model image")
    parser.add_argument("jewelry_image", type=Path, help="Path to the jewelry image")
    return parser.parse_args()


def validate_image_path(path: Path, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"{label} must use one of: {supported}")


def main() -> None:
    load_dotenv()
    args = parse_args()
    validate_image_path(args.model_image, "Model image")
    validate_image_path(args.jewelry_image, "Jewelry image")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env or your shell.")

    client = OpenAI()
    with args.model_image.open("rb") as model_image, args.jewelry_image.open(
        "rb"
    ) as jewelry_image:
        response = client.images.edit(
            model="gpt-image-2.5-sunburst",
            image=[model_image, jewelry_image],
            prompt=PROMPT,
            quality="low",
        )

    if not response.data or not response.data[0].b64_json:
        raise RuntimeError("OpenAI returned no image data.")

    Path("output.png").write_bytes(base64.b64decode(response.data[0].b64_json))
    print("Saved generated image to output.png")


if __name__ == "__main__":
    main()
