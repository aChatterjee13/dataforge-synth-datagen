from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
import os
import json
import uuid
import pandas as pd

from app.api.models import MultiTableUploadResponse
from app.db.database import get_db, Job, JobStatusEnum, SessionLocal
from app.utils.file_handler import load_data
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/upload-multi", response_model=MultiTableUploadResponse)
async def upload_multi_table(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Upload multiple CSV files for multi-table synthesis"""
    for f in files:
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in ['.csv', '.xlsx', '.xls']:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {f.filename}")

    try:
        job_id = str(uuid.uuid4())
        upload_dir = os.path.join("uploads", job_id)
        os.makedirs(upload_dir, exist_ok=True)

        tables_info = {}
        total_rows = 0

        for f in files:
            file_path = os.path.join(upload_dir, f.filename)
            content = await f.read()
            with open(file_path, "wb") as fp:
                fp.write(content)

            df = load_data(file_path)
            table_name = os.path.splitext(f.filename)[0]

            column_types = {}
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    column_types[col] = "numeric"
                elif pd.api.types.is_datetime64_any_dtype(df[col]):
                    column_types[col] = "datetime"
                else:
                    column_types[col] = "categorical"

            tables_info[table_name] = {
                "rows": len(df),
                "columns": len(df.columns),
                "column_types": column_types,
                "filename": f.filename
            }
            total_rows += len(df)

        # Create job
        job = Job(
            id=job_id,
            filename=f"{len(files)} tables",
            original_path=upload_dir,
            status=JobStatusEnum.PENDING,
            rows_original=total_rows,
            columns=len(files)
        )
        db.add(job)
        db.commit()

        return MultiTableUploadResponse(
            job_id=job_id,
            tables=tables_info,
            message=f"Uploaded {len(files)} tables with {total_rows} total rows"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-multi")
async def generate_multi_table(
    request: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start multi-table synthetic data generation"""
    job_id = request.get("job_id")
    config = request.get("config", {})

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatusEnum.PENDING:
        raise HTTPException(status_code=400, detail="Job already processing or completed")

    job.model_type = "hma"
    job.status = JobStatusEnum.PROCESSING
    job.message = "Starting multi-table generation..."
    job.config_json = json.dumps(config)
    db.commit()

    background_tasks.add_task(
        _generate_multi_table_background,
        job_id=job_id,
        upload_dir=job.original_path,
        config=config
    )

    return {"job_id": job_id, "status": "processing", "message": "Multi-table generation started"}


def _generate_multi_table_background(job_id: str, upload_dir: str, config: dict):
    """Background task for multi-table generation"""
    from app.services.multi_table_generator import generate_multi_table_synthetic

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        # Load all tables
        tables = {}
        for fname in os.listdir(upload_dir):
            if fname.endswith(('.csv', '.xlsx', '.xls')):
                fpath = os.path.join(upload_dir, fname)
                table_name = os.path.splitext(fname)[0]
                tables[table_name] = load_data(fpath)

        relationships = config.get("relationships", [])
        num_rows = config.get("num_rows", 1000)
        epochs = config.get("epochs", 300)

        def progress_cb(pct, msg):
            job.progress = pct
            job.message = msg
            db.commit()

        synthetic_tables = generate_multi_table_synthetic(
            tables, relationships, num_rows, epochs, progress_cb
        )

        # Save synthetic tables
        output_dir = os.path.join("outputs", job_id)
        os.makedirs(output_dir, exist_ok=True)

        total_rows = 0
        for name, df in synthetic_tables.items():
            df.to_csv(os.path.join(output_dir, f"{name}.csv"), index=False)
            total_rows += len(df)

        job.status = JobStatusEnum.COMPLETED
        job.progress = 100
        job.rows_generated = total_rows
        job.message = f"Generated {len(synthetic_tables)} tables with {total_rows} total rows"
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        if job:
            job.status = JobStatusEnum.FAILED
            job.error = str(e)
            job.message = f"Multi-table generation failed: {e}"
            db.commit()
    finally:
        db.close()
