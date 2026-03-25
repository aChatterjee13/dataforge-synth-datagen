from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import json
import uuid

from app.api.models import GenerateRequest, CDCResultsResponse
from app.db.database import get_db, Job, JobStatusEnum
from app.services.db_test_generator import DBSchemaParser
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/upload-cdc-schema")
async def upload_cdc_schema(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a database schema for CDC event generation"""
    allowed_extensions = ['.sql', '.ddl', '.json', '.yaml', '.yml']
    file_extension = os.path.splitext(file.filename)[1].lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
        )

    try:
        job_id = str(uuid.uuid4())
        upload_dir = os.path.join("uploads")
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, f"{job_id}{file_extension}")

        with open(filepath, "wb") as f:
            content = await file.read()
            f.write(content)

        schema_info = DBSchemaParser.analyze_schema_info(filepath)

        job = Job(
            id=job_id,
            filename=file.filename,
            original_path=filepath,
            status=JobStatusEnum.PENDING,
            rows_original=schema_info.get('total_tables', 0),
            columns=schema_info.get('total_columns', 0)
        )
        db.add(job)
        db.commit()

        return {
            "job_id": job_id,
            "filename": file.filename,
            "schema_info": schema_info,
            "message": f"Schema uploaded: {schema_info.get('total_tables', 0)} tables"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-cdc")
async def generate_cdc(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start CDC event generation"""
    job = db.query(Job).filter(Job.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatusEnum.PENDING:
        raise HTTPException(status_code=400, detail="Job already processing or completed")

    job.model_type = 'cdc_gen'
    job.status = JobStatusEnum.PROCESSING
    job.message = "Starting CDC event generation..."
    job.config_json = json.dumps(request.config.dict())
    db.commit()

    from app.services.cdc_generator import generate_cdc_background
    background_tasks.add_task(
        generate_cdc_background,
        job_id=request.job_id,
        schema_path=job.original_path,
        config=request.config.dict()
    )

    return {"job_id": request.job_id, "status": "processing", "message": "CDC generation started"}


@router.get("/cdc-results/{job_id}", response_model=CDCResultsResponse)
async def get_cdc_results(job_id: str, db: Session = Depends(get_db)):
    """Get CDC generation results"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatusEnum.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet")

    results_path = os.path.join("outputs", job_id, "results.json")
    if not os.path.exists(results_path):
        raise HTTPException(status_code=404, detail="Results not found")

    with open(results_path, 'r') as f:
        results = json.load(f)

    return CDCResultsResponse(
        job_id=job_id,
        summary=results.get('summary', {}),
        event_distribution=results.get('event_distribution', {}),
        sample_events=results.get('sample_events', [])
    )


@router.get("/download-cdc/{job_id}")
async def download_cdc(job_id: str, db: Session = Depends(get_db)):
    """Download CDC events"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatusEnum.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet")

    output_dir = os.path.join("outputs", job_id)
    for fname in ['cdc_events.json', 'cdc_events.sql', 'cdc_events.csv']:
        filepath = os.path.join(output_dir, fname)
        if os.path.exists(filepath):
            media = "application/json" if fname.endswith('.json') else "text/plain"
            return FileResponse(filepath, media_type=media, filename=f"cdc_{job_id[:8]}_{fname}")

    raise HTTPException(status_code=404, detail="CDC events file not found")
