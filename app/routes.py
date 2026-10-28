"""FastAPI routes for uploads, models, and generation jobs."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai import MODEL_DIR, MODELS_FILE, run_generation
from app.db import get_db
from app.image_utils import remove_background, validate_upload
from app.models import Generation, Upload


ROOT_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = ROOT_DIR / "storage" / "uploads"


class GenerateRequest(BaseModel):
    upload_id: str
    model_id: str
    quality: str = Field(default="low", pattern="^(low|medium|high)$")


def load_models() -> list[dict]:
    return json.loads(MODELS_FILE.read_text(encoding="utf-8"))


def find_model(model_id: str) -> dict | None:
    return next((model for model in load_models() if model["id"] == model_id), None)


async def upload_jewelry(
    file: UploadFile = File(...),
    jewelry_type: str = Form(...),
    db: Session = Depends(get_db),
):
    if jewelry_type not in {"earrings", "necklace", "ring", "bracelet"}:
        raise HTTPException(status_code=400, detail="Invalid jewelry type.")
    data = await file.read()
    try:
        validate_upload(file.filename or "", file.content_type, data)
        upload_id = str(uuid.uuid4())
        original_path = UPLOAD_DIR / f"{upload_id}{Path(file.filename or '').suffix.lower()}"
        cutout_path = UPLOAD_DIR / f"{upload_id}-cutout.png"
        original_path.write_bytes(data)
        cutout_path.write_bytes(remove_background(data))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Could not save uploaded image.") from exc

    db.add(
        Upload(
            id=upload_id,
            original_path=str(original_path),
            cutout_path=str(cutout_path),
            jewelry_type=jewelry_type,
        )
    )
    db.commit()
    return {"upload_id": upload_id}


def list_models(body_part: str | None = None):
    models = load_models()
    if body_part:
        models = [model for model in models if model["body_part"] == body_part]
    return {"models": models}


def create_generation(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if db.get(Upload, request.upload_id) is None:
        raise HTTPException(status_code=404, detail="Upload not found.")
    model = find_model(request.model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found.")
    generation = Generation(
        id=str(uuid.uuid4()),
        upload_id=request.upload_id,
        model_id=request.model_id,
        quality=request.quality,
        status="queued",
    )
    db.add(generation)
    db.commit()
    background_tasks.add_task(run_generation, db, generation.id)
    return {"job_id": generation.id}


def get_job(job_id: str, db: Session = Depends(get_db)):
    generation = db.get(Generation, job_id)
    if generation is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    result_url = None
    if generation.result_path:
        result_url = f"/storage/results/{Path(generation.result_path).name}"
    return {
        "status": generation.status,
        "result_url": result_url,
        "error": generation.error,
    }
