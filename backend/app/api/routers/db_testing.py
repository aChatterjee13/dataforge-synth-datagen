from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
import os
import json
import uuid
import zipfile
from io import BytesIO

from app.api.models import UploadResponse, GenerateRequest, DataType, DBTestResultsResponse
from app.db.database import get_db, Job, JobStatusEnum
from app.services.db_test_generator import DBSchemaParser, generate_db_tests_background
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/upload-db-schema", response_model=UploadResponse)
async def upload_db_schema(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a database schema file (SQL DDL, JSON, or YAML)"""
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

        return UploadResponse(
            job_id=job_id,
            filename=file.filename,
            rows=schema_info.get('total_tables', 0),
            columns=schema_info.get('total_columns', 0),
            column_types={},
            data_type=DataType.DATA_TESTING,
            message=f"Schema uploaded: {schema_info.get('total_tables', 0)} tables, {schema_info.get('total_columns', 0)} columns"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-db-tests")
async def generate_db_tests(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start database test data generation"""
    job = db.query(Job).filter(Job.id == request.job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatusEnum.PENDING:
        raise HTTPException(status_code=400, detail="Job already processing or completed")

    config = request.config
    if not config.gpt_api_key and not os.getenv('OPENAI_API_KEY'):
        raise HTTPException(
            status_code=400,
            detail="GPT API key not provided. Set OPENAI_API_KEY or provide gpt_api_key in config"
        )

    job.model_type = 'gpt_data_test'
    job.status = JobStatusEnum.PROCESSING
    job.message = "Starting database test data generation..."

    job.config_json = json.dumps(config.dict())
    db.commit()

    config_dict = config.dict()
    config_dict['gpt_api_key'] = config.gpt_api_key or os.getenv('OPENAI_API_KEY')

    background_tasks.add_task(
        generate_db_tests_background,
        job_id=request.job_id,
        schema_path=job.original_path,
        config=config_dict
    )

    return {"job_id": request.job_id, "status": "processing", "message": "Database test generation started"}


@router.get("/db-test-results/{job_id}", response_model=DBTestResultsResponse)
async def get_db_test_results(job_id: str, db: Session = Depends(get_db)):
    """Get database test generation results"""
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

    return DBTestResultsResponse(
        job_id=job_id,
        summary={
            'total_tables': results.get('total_tables', 0),
            'total_inserts': results.get('total_inserts', 0),
            'total_violations': results.get('total_violations', 0),
            'dialect': results.get('dialect', 'postgresql'),
            'validation_score': results.get('validation', {}).get('validation_score', 0)
        },
        table_details=results.get('table_details', {}),
        sample_inserts=results.get('sample_inserts'),
        sample_violations=results.get('sample_violations'),
        validation=results.get('validation'),
        dependency_order=results.get('dependency_order')
    )


@router.get("/download-db-tests/{job_id}")
async def download_db_tests(
    job_id: str,
    type: str = "all",
    db: Session = Depends(get_db)
):
    """Download database test outputs"""
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatusEnum.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet")

    output_dir = os.path.join("outputs", job_id)

    if type == "inserts":
        filepath = os.path.join(output_dir, "inserts.sql")
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Inserts file not found")
        return FileResponse(filepath, media_type="text/plain", filename=f"inserts_{job_id[:8]}.sql")

    elif type == "violations":
        filepath = os.path.join(output_dir, "violations.sql")
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Violations file not found")
        return FileResponse(filepath, media_type="text/plain", filename=f"violations_{job_id[:8]}.sql")

    else:
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fname in os.listdir(output_dir):
                fpath = os.path.join(output_dir, fname)
                if os.path.isfile(fpath):
                    zf.write(fpath, fname)

        zip_buffer.seek(0)
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=db_tests_{job_id[:8]}.zip"}
        )
