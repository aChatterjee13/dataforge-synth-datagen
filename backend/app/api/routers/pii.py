from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import json

from app.api.models import GenerateRequest, PIIUploadResponse, PIIColumnDetection, PIIResultsResponse
from app.db.database import get_db, Job, JobStatusEnum
from app.utils.file_handler import save_upload_file, load_data
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/upload-pii", response_model=PIIUploadResponse)
async def upload_pii_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a dataset for PII detection and masking"""
    allowed_extensions = ['.csv', '.xlsx', '.xls']
    file_extension = os.path.splitext(file.filename)[1].lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
        )

    try:
        job_id, filepath = save_upload_file(file.file, file.filename)
        df = load_data(filepath)

        from app.services.pii_masker import PIIDetector
        detections = PIIDetector.detect_pii_columns(df)
        pii_col_names = [d['column_name'] for d in detections]
        non_pii = PIIDetector.get_non_pii_columns(df, pii_col_names)

        job = Job(
            id=job_id,
            filename=file.filename,
            original_path=filepath,
            status=JobStatusEnum.PENDING,
            rows_original=len(df),
            columns=len(df.columns)
        )
        db.add(job)
        db.commit()

        return PIIUploadResponse(
            job_id=job_id,
            filename=file.filename,
            rows=len(df),
            columns=len(df.columns),
            detected_pii_columns=[PIIColumnDetection(**d) for d in detections],
            non_pii_columns=non_pii
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-pii-mask")
async def generate_pii_mask(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start PII masking / anonymization"""
    job = db.query(Job).filter(Job.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatusEnum.PENDING:
        raise HTTPException(status_code=400, detail="Job already processing or completed")

    job.model_type = 'pii_mask'
    job.status = JobStatusEnum.PROCESSING
    job.message = "Starting PII masking..."
    job.config_json = json.dumps(request.config.dict())
    db.commit()

    from app.services.pii_masker import generate_pii_mask_background
    background_tasks.add_task(
        generate_pii_mask_background,
        job_id=request.job_id,
        original_path=job.original_path,
        config=request.config.dict()
    )

    return {"job_id": request.job_id, "status": "processing", "message": "PII masking started"}


@router.get("/pii-results/{job_id}", response_model=PIIResultsResponse)
async def get_pii_results(job_id: str, db: Session = Depends(get_db)):
    """Get PII masking results"""
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

    return PIIResultsResponse(
        job_id=job_id,
        summary=results.get('summary', {}),
        column_reports=results.get('column_reports', []),
        privacy_assessment=results.get('privacy_assessment', {})
    )


@router.get("/download-pii/{job_id}")
async def download_pii_masked(job_id: str, db: Session = Depends(get_db)):
    """Download masked/anonymized dataset"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatusEnum.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet")

    filepath = os.path.join("outputs", job_id, "masked_data.csv")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Masked file not found")

    return FileResponse(
        filepath,
        media_type="text/csv",
        filename=f"{os.path.splitext(job.filename)[0]}_masked.csv"
    )
