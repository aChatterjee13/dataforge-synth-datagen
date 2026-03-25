from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import json
import uuid

from app.api.models import GenerateRequest, LogUploadResponse, LogFormatInfo, LogResultsResponse
from app.db.database import get_db, Job, JobStatusEnum
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/upload-logs", response_model=LogUploadResponse)
async def upload_logs(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a log file for synthesis"""
    allowed_extensions = ['.log', '.txt', '.json', '.csv']
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

        content = await file.read()
        with open(filepath, "wb") as f:
            f.write(content)

        from app.services.log_synthesizer import LogParser
        text_content = content.decode('utf-8', errors='replace')
        fmt = LogParser.detect_format(text_content)
        records = LogParser.parse_logs(text_content, fmt)
        distributions = LogParser.analyze_distributions(records)

        lines = [l for l in text_content.strip().split('\n') if l.strip()]

        format_info = LogFormatInfo(
            detected_format=fmt,
            total_lines=len(lines),
            fields=list(distributions.keys()),
            sample_lines=lines[:5],
            distributions={
                k: {'unique': v.get('unique', 0), 'top_3': [tv['value'] for tv in v.get('top_values', [])[:3]]}
                for k, v in distributions.items()
            }
        )

        job = Job(
            id=job_id,
            filename=file.filename,
            original_path=filepath,
            status=JobStatusEnum.PENDING,
            rows_original=len(lines),
            columns=len(distributions)
        )
        db.add(job)
        db.commit()

        return LogUploadResponse(
            job_id=job_id,
            filename=file.filename,
            format_info=format_info
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-logs")
async def generate_logs(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start synthetic log generation"""
    job = db.query(Job).filter(Job.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatusEnum.PENDING:
        raise HTTPException(status_code=400, detail="Job already processing or completed")

    job.model_type = 'log_synth'
    job.status = JobStatusEnum.PROCESSING
    job.message = "Starting log synthesis..."
    job.config_json = json.dumps(request.config.dict())
    db.commit()

    from app.services.log_synthesizer import generate_logs_background
    background_tasks.add_task(
        generate_logs_background,
        job_id=request.job_id,
        original_path=job.original_path,
        config=request.config.dict()
    )

    return {"job_id": request.job_id, "status": "processing", "message": "Log synthesis started"}


@router.get("/log-results/{job_id}", response_model=LogResultsResponse)
async def get_log_results(job_id: str, db: Session = Depends(get_db)):
    """Get log synthesis results"""
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

    return LogResultsResponse(
        job_id=job_id,
        summary=results.get('summary', {}),
        analysis=results.get('analysis', {}),
        sample_logs=results.get('sample_logs', [])
    )


@router.get("/download-logs/{job_id}")
async def download_logs(job_id: str, db: Session = Depends(get_db)):
    """Download generated synthetic logs"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatusEnum.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet")

    output_dir = os.path.join("outputs", job_id)
    for ext in ['.json', '.log']:
        filepath = os.path.join(output_dir, f"synthetic_logs{ext}")
        if os.path.exists(filepath):
            return FileResponse(
                filepath,
                media_type="text/plain",
                filename=f"synthetic_logs_{job_id[:8]}{ext}"
            )

    raise HTTPException(status_code=404, detail="Log file not found")
