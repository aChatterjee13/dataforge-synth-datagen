from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import os
import json
import pandas as pd

from app.api.models import PreviewData
from app.db.database import get_db, Job, JobStatusEnum, SessionLocal
from app.utils.file_handler import get_output_path
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/stream-generate/{job_id}")
async def stream_generate(job_id: str, db: Session = Depends(get_db)):
    """SSE endpoint that streams generation progress"""
    from sse_starlette.sse import EventSourceResponse
    import asyncio

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        while True:
            db_session = SessionLocal()
            try:
                current_job = db_session.query(Job).filter(Job.id == job_id).first()
                if not current_job:
                    yield {"event": "error", "data": json.dumps({"error": "Job not found"})}
                    break

                data = {
                    "status": current_job.status.value,
                    "progress": current_job.progress,
                    "message": current_job.message,
                    "rows_generated": current_job.rows_generated or 0,
                }

                yield {"event": "progress", "data": json.dumps(data)}

                if current_job.status in [JobStatusEnum.COMPLETED, JobStatusEnum.FAILED]:
                    yield {"event": "complete", "data": json.dumps(data)}
                    break
            finally:
                db_session.close()

            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


@router.get("/preview/{job_id}", response_model=PreviewData)
async def get_preview(job_id: str, n: int = 20, db: Session = Depends(get_db)):
    """Get preview of generated data so far"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    output_path = get_output_path(job_id)

    if not os.path.exists(output_path):
        return PreviewData(
            job_id=job_id,
            rows_generated=0,
            total_requested=job.num_rows or 0,
            sample_data=[],
            is_complete=False
        )

    try:
        df = pd.read_csv(output_path, nrows=n)
        sample_data = json.loads(df.to_json(orient='records', date_format='iso'))

        return PreviewData(
            job_id=job_id,
            rows_generated=job.rows_generated or len(df),
            total_requested=job.num_rows or 0,
            sample_data=sample_data,
            is_complete=job.status == JobStatusEnum.COMPLETED
        )
    except Exception:
        return PreviewData(
            job_id=job_id,
            rows_generated=0,
            total_requested=job.num_rows or 0,
            sample_data=[],
            is_complete=False
        )
