from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
import json

from app.api.models import GenerateRequest
from app.db.database import get_db, Job, JobStatusEnum
from app.services.generator import generate_synthetic_data_background
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/generate-conditional")
async def generate_conditional(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start conditional synthetic data generation"""
    job = db.query(Job).filter(Job.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatusEnum.PENDING:
        raise HTTPException(status_code=400, detail="Job already processing or completed")

    job.model_type = request.config.model_type.value
    job.epochs = request.config.epochs
    job.batch_size = request.config.batch_size
    job.num_rows = request.config.num_rows
    job.status = JobStatusEnum.PROCESSING
    job.message = "Starting conditional generation..."
    job.config_json = json.dumps(request.config.dict())
    db.commit()

    background_tasks.add_task(
        generate_synthetic_data_background,
        job_id=request.job_id,
        original_path=job.original_path,
        config=request.config
    )

    return {"job_id": request.job_id, "status": "processing", "message": "Conditional generation started"}
