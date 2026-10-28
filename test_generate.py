"""Run a standalone low-quality JewelryTryOn image generation."""

from __future__ import annotations

import argparse
import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


PROMPT = (
    "Put the jewelry from the second image on the person in the first image. "
    "Keep the jewelry design EXACTLY the same: same shape, stones, chain and colors. "
    "Do not change the person's face, pose or background. "
    "Use realistic lighting and natural shadows on the skin."
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
            model="gpt-image-1",
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
