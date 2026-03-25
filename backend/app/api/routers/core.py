from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import json

from app.api.models import (
    UploadResponse, GenerateRequest, JobStatusResponse,
    ValidationResponse, JobListResponse, JobListItem, JobStatus,
)
from app.db.database import get_db, Job, JobStatusEnum
from app.utils.file_handler import save_upload_file, load_data, analyze_dataframe, get_output_path
from app.services.generator import generate_synthetic_data_background
from app.services.validator import validate_synthetic_data
from app.utils.logger import get_logger
from app.middleware import get_request_id_from_request

logger = get_logger(__name__)
router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_dataset(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a dataset for synthetic data generation"""
    request_id = get_request_id_from_request(request)

    logger.info(f"Processing file upload", extra={
        'extra_data': {
            'filename': file.filename,
            'content_type': file.content_type
        }
    })

    # Validate file extension
    allowed_extensions = ['.csv', '.xlsx', '.xls']
    file_extension = os.path.splitext(file.filename)[1].lower()

    if file_extension not in allowed_extensions:
        logger.warning(f"Invalid file type uploaded", extra={
            'extra_data': {
                'filename': file.filename,
                'extension': file_extension,
                'allowed': allowed_extensions
            }
        })
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
        )

    try:
        # Save file
        job_id, filepath = save_upload_file(file.file, file.filename)

        logger.info(f"File saved", extra={
            'extra_data': {
                'job_id': job_id,
                'filepath': filepath
            }
        })

        # Load and analyze data
        df = load_data(filepath)
        metadata = analyze_dataframe(df)

        logger.info(f"Data analyzed", extra={
            'extra_data': {
                'job_id': job_id,
                'rows': metadata["rows"],
                'columns': metadata["columns"]
            }
        })

        # Create job in database
        job = Job(
            id=job_id,
            filename=file.filename,
            original_path=filepath,
            status=JobStatusEnum.PENDING,
            rows_original=metadata["rows"],
            columns=metadata["columns"]
        )
        db.add(job)
        db.commit()

        logger.info(f"Job created successfully", extra={
            'extra_data': {
                'job_id': job_id,
                'filename': file.filename,
                'rows': metadata["rows"]
            }
        })

        # Get sample data (first 10 rows) for preview
        sample_data = None
        try:
            sample_df = df.head(10)
            sample_data = json.loads(sample_df.to_json(orient='records', date_format='iso'))
        except Exception as sample_err:
            logger.warning(f"Could not generate sample data: {sample_err}")

        return UploadResponse(
            job_id=job_id,
            filename=file.filename,
            rows=metadata["rows"],
            columns=metadata["columns"],
            column_types=metadata["column_types"],
            sample_data=sample_data,
            potential_targets=metadata.get("potential_targets"),
            is_timeseries=metadata.get("is_timeseries", False),
            timeseries_info=metadata.get("timeseries_info"),
            message="File uploaded successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed", exc_info=True, extra={
            'extra_data': {
                'filename': file.filename,
                'error': str(e)
            }
        })
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_synthetic(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start synthetic data generation"""
    job = db.query(Job).filter(Job.id == request.job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatusEnum.PENDING:
        raise HTTPException(status_code=400, detail="Job already processing or completed")

    # Update job with configuration
    job.model_type = request.config.model_type.value
    job.epochs = request.config.epochs
    job.batch_size = request.config.batch_size
    job.num_rows = request.config.num_rows
    job.status = JobStatusEnum.PROCESSING
    job.message = "Starting generation..."

    # Store full config as JSON including ml_target_variables
    config_dict = request.config.dict()
    if config_dict.get('ml_target_variables'):
        config_dict['ml_target_variables'] = [
            {
                'column_name': t['column_name'],
                'task_type': t['task_type'],
                'enabled': t['enabled']
            }
            for t in config_dict['ml_target_variables']
        ]
    job.config_json = json.dumps(config_dict)

    db.commit()

    # Start background generation
    background_tasks.add_task(
        generate_synthetic_data_background,
        job_id=request.job_id,
        original_path=job.original_path,
        config=request.config
    )

    return {
        "job_id": request.job_id,
        "status": "processing",
        "message": "Synthetic data generation started"
    }


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Get job status"""
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job.id,
        status=JobStatus(job.status.value),
        progress=job.progress,
        message=job.message,
        model_type=job.model_type,
        created_at=job.created_at,
        completed_at=job.completed_at,
        error=job.error
    )


@router.get("/download/{job_id}")
async def download_synthetic_data(job_id: str, db: Session = Depends(get_db)):
    """Download generated synthetic data"""
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatusEnum.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet")

    filepath = get_output_path(job_id)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Generated file not found")

    return FileResponse(
        filepath,
        media_type="text/csv",
        filename=f"{os.path.splitext(job.filename)[0]}_synthetic.csv"
    )


@router.get("/validation/{job_id}", response_model=ValidationResponse)
async def get_validation_metrics(job_id: str, db: Session = Depends(get_db)):
    """Get validation metrics for generated data"""
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatusEnum.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet")

    try:
        # Load original and synthetic data
        original_df = load_data(job.original_path)
        synthetic_df = load_data(get_output_path(job_id))

        # Extract target variables from stored config if available
        target_variables = None
        if job.config_json:
            try:
                config_data = json.loads(job.config_json)
                if config_data.get('ml_target_variables'):
                    target_variables = [
                        t for t in config_data['ml_target_variables']
                        if t.get('enabled', True)
                    ]
                    logger.info(f"Using user-specified targets: {target_variables}")
            except Exception as e:
                logger.error(f"Error parsing config JSON: {e}")

        # Validate with target variables
        validation_results = validate_synthetic_data(
            original_df,
            synthetic_df,
            target_variables=target_variables
        )

        # Cache validation scores in DB
        job.quality_score = validation_results["metrics"]["quality_score"]
        job.privacy_score = validation_results["metrics"]["privacy_score"]
        job.correlation_score = validation_results["metrics"]["correlation_preservation"]
        db.commit()

        return ValidationResponse(
            job_id=job_id,
            metrics=validation_results["metrics"],
            assessment_summary=validation_results["assessment_summary"],
            charts=validation_results["charts"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(db: Session = Depends(get_db)):
    """List all jobs"""
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()

    job_items = [
        JobListItem(
            job_id=job.id,
            filename=job.filename,
            status=JobStatus(job.status.value),
            created_at=job.created_at,
            rows_original=job.rows_original,
            rows_generated=job.rows_generated,
            model_type=job.model_type,
            quality_score=job.quality_score
        )
        for job in jobs
    ]

    return JobListResponse(jobs=job_items, total=len(job_items))


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, db: Session = Depends(get_db)):
    """Delete a job and its files"""
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Delete files
    if os.path.exists(job.original_path):
        os.remove(job.original_path)

    synthetic_path = get_output_path(job_id)
    if os.path.exists(synthetic_path):
        os.remove(synthetic_path)

    # Delete from database
    db.delete(job)
    db.commit()

    return {"message": "Job deleted successfully"}
