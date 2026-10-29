"""OpenAI image generation and generation-job orchestration."""

from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from app.db import SessionLocal
from app.image_utils import create_fallback_composite
from app.models import Generation, Upload


load_dotenv()
ROOT_DIR = Path(__file__).resolve().parent.parent
MODELS_FILE = ROOT_DIR / "models.json"
MODEL_DIR = ROOT_DIR / "storage" / "models"
RESULT_DIR = ROOT_DIR / "storage" / "results"
GENERATION_PROMPT = (
    "Create a professional jewelry catalog try-on photo. "
    "The first image is the model; the second image is the jewelry product. "
    "Place the jewelry from the second image onto the model so it looks naturally worn: "
    "earrings on the earlobe, necklace around the neck, ring on a finger, or bracelet on the wrist. "
    "Preserve the jewelry design EXACTLY: same shape, metal color, stones, size proportions, and details. "
    "Keep the model's face, skin tone, pose, hair, and background unchanged. "
    "Match lighting and add soft realistic contact shadows and metal reflections on the skin. "
    "Photorealistic close-up lifestyle product photography, sharp jewelry focus, natural skin texture."
)
FALLBACK_PROMPT = (
    "Create a photorealistic jewelry catalog photo of this jewelry worn naturally on the model. "
    "Match lighting and soft contact shadows. Do not change the jewelry design."
)
ESTIMATED_COSTS = {"low": 0.02, "medium": 0.07, "high": 0.19}


def load_model(model_id: str) -> dict:
    models = json.loads(MODELS_FILE.read_text(encoding="utf-8"))
    for model in models:
        if model["id"] == model_id:
            return model
    raise ValueError("Model not found.")


def generate_image(upload: Upload, generation: Generation) -> bytes:
    model = load_model(generation.model_id)
    model_path = ROOT_DIR / model["image"]
    if not model_path.is_file():
        raise FileNotFoundError(f"Model image is missing: {model_path}")

    use_fallback = os.getenv("USE_PASTE_FALLBACK", "false").lower() == "true"
    prompt = GENERATION_PROMPT
    image_paths = [model_path, Path(upload.cutout_path)]
    composite_path: Path | None = None

    if use_fallback:
        composite = create_fallback_composite(
            model_path,
            Path(upload.cutout_path),
            model["position"],
            model["scale"],
        )
        composite_path = RESULT_DIR / f"{generation.id}-composite.png"
        composite_path.write_bytes(composite)
        image_paths = [composite_path]
        prompt = FALLBACK_PROMPT

    client = OpenAI()
    try:
        with image_paths[0].open("rb") as first_image:
            handles = [first_image]
            if len(image_paths) > 1:
                second_image = image_paths[1].open("rb")
                handles.append(second_image)
            else:
                second_image = None
            try:
                response = client.images.edit(
                    model="gpt-image-2.5-sunburst",
                    image=handles,
                    prompt=prompt,
                    quality=generation.quality,
                )
            finally:
                if second_image:
                    second_image.close()
    finally:
        if composite_path:
            composite_path.unlink(missing_ok=True)

    if not response.data or not response.data[0].b64_json:
        raise RuntimeError("OpenAI returned no image data.")
    return base64.b64decode(response.data[0].b64_json)


def run_generation(generation_id: str) -> None:
    """Process a generation job using a fresh DB session."""
    with SessionLocal() as db:
        generation = db.get(Generation, generation_id)
        if generation is None:
            return
        generation.status = "processing"
        db.commit()
        print(
            f"Estimated generation cost for {generation.id}: "
            f"${ESTIMATED_COSTS[generation.quality]:.2f} ({generation.quality})"
        )

        try:
            upload = db.get(Upload, generation.upload_id)
            if upload is None:
                raise RuntimeError("The upload associated with this job no longer exists.")
            last_error: Exception | None = None
            for attempt in range(3):
                try:
                    result = generate_image(upload, generation)
                    result_path = RESULT_DIR / f"{generation.id}.png"
                    result_path.write_bytes(result)
                    generation.result_path = str(result_path)
                    generation.status = "done"
                    db.commit()
                    return
                except Exception as exc:
                    last_error = exc
                    if attempt < 2:
                        time.sleep(2**attempt)
            raise RuntimeError(f"Image generation failed after 2 retries: {last_error}")
        except Exception as exc:
            generation.status = "failed"
            generation.error = str(exc)
            db.commit()
