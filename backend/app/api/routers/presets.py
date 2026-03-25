from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import json

from app.api.models import PresetCreate, PresetResponse
from app.db.database import get_db, Preset
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

BUILTIN_PRESETS = [
    {
        "id": -1,
        "name": "Quick Preview",
        "description": "Fast generation with GaussianCopula for quick previews",
        "config": {"model_type": "gaussian_copula", "num_rows": 500, "epochs": 100, "batch_size": 500},
        "is_builtin": True,
    },
    {
        "id": -2,
        "name": "High Quality",
        "description": "Best quality using CTGAN with more epochs",
        "config": {"model_type": "ctgan", "num_rows": 1000, "epochs": 500, "batch_size": 500},
        "is_builtin": True,
    },
    {
        "id": -3,
        "name": "Privacy First",
        "description": "CTGAN with differential privacy enabled",
        "config": {"model_type": "ctgan", "num_rows": 1000, "epochs": 300, "batch_size": 500, "enable_privacy": True, "privacy_epsilon": 0.5},
        "is_builtin": True,
    },
    {
        "id": -4,
        "name": "Time Series",
        "description": "TimeGAN for temporal data patterns",
        "config": {"model_type": "timegan", "num_rows": 1000, "epochs": 300, "batch_size": 500},
        "is_builtin": True,
    },
    {
        "id": -5,
        "name": "State of the Art (TabDDPM)",
        "description": "Diffusion-based model with state-of-the-art quality",
        "config": {"model_type": "tab_ddpm", "num_rows": 1000, "epochs": 500, "batch_size": 500},
        "is_builtin": True,
    },
    {
        "id": -6,
        "name": "LLM Prototyping",
        "description": "Fast GPT-based generation for demos and prototyping",
        "config": {"model_type": "llm_row_gen", "num_rows": 500, "use_case": "prototyping"},
        "is_builtin": True,
    },
    {
        "id": -7,
        "name": "Privacy Native (DP-CTGAN)",
        "description": "Differential privacy baked into training",
        "config": {"model_type": "dp_ctgan", "num_rows": 1000, "epochs": 300, "enable_privacy": True, "privacy_epsilon": 1.0},
        "is_builtin": True,
    },
]


@router.get("/presets", response_model=List[PresetResponse])
async def list_presets(db: Session = Depends(get_db)):
    """List all presets (built-in + user-saved)"""
    result = [PresetResponse(**p) for p in BUILTIN_PRESETS]

    user_presets = db.query(Preset).order_by(Preset.created_at.desc()).all()
    for p in user_presets:
        result.append(PresetResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            config=json.loads(p.config_json),
            is_builtin=False,
            created_at=p.created_at
        ))

    return result


@router.post("/presets", response_model=PresetResponse)
async def create_preset(preset: PresetCreate, db: Session = Depends(get_db)):
    """Save a new preset"""
    db_preset = Preset(
        name=preset.name,
        description=preset.description,
        config_json=json.dumps(preset.config)
    )
    db.add(db_preset)
    db.commit()
    db.refresh(db_preset)

    return PresetResponse(
        id=db_preset.id,
        name=db_preset.name,
        description=db_preset.description,
        config=json.loads(db_preset.config_json),
        is_builtin=False,
        created_at=db_preset.created_at
    )


@router.delete("/presets/{preset_id}")
async def delete_preset(preset_id: int, db: Session = Depends(get_db)):
    """Delete a user-saved preset"""
    if preset_id < 0:
        raise HTTPException(status_code=400, detail="Cannot delete built-in presets")

    preset = db.query(Preset).filter(Preset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")

    db.delete(preset)
    db.commit()
    return {"message": "Preset deleted successfully"}
