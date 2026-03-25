from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import json
import uuid

from app.api.models import UploadResponse, GenerateRequest, DataType, APITestResultsResponse
from app.db.database import get_db, Job, JobStatusEnum
from app.services.api_test_generator import OpenAPISpecParser, generate_api_tests_background
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/upload-api-spec", response_model=UploadResponse)
async def upload_api_spec(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload an OpenAPI/Swagger specification file"""
    allowed_extensions = ['.json', '.yaml', '.yml']
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

        spec_info = OpenAPISpecParser.analyze_spec_info(filepath)

        job = Job(
            id=job_id,
            filename=file.filename,
            original_path=filepath,
            status=JobStatusEnum.PENDING,
            rows_original=spec_info.get('total_endpoints', 0),
            columns=spec_info.get('schema_count', 0)
        )
        db.add(job)
        db.commit()

        return UploadResponse(
            job_id=job_id,
            filename=file.filename,
            rows=spec_info.get('total_endpoints', 0),
            columns=spec_info.get('schema_count', 0),
            column_types={},
            data_type=DataType.API_TESTING,
            message=f"API spec uploaded: {spec_info.get('title', 'Unknown')} - {spec_info.get('total_endpoints', 0)} endpoints"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-api-tests")
async def generate_api_tests(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start API test generation"""
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

    job.model_type = 'gpt_api_test'
    job.status = JobStatusEnum.PROCESSING
    job.message = "Starting API test generation..."

    job.config_json = json.dumps(config.dict())
    db.commit()

    config_dict = config.dict()
    config_dict['gpt_api_key'] = config.gpt_api_key or os.getenv('OPENAI_API_KEY')

    background_tasks.add_task(
        generate_api_tests_background,
        job_id=request.job_id,
        spec_path=job.original_path,
        config=config_dict
    )

    return {"job_id": request.job_id, "status": "processing", "message": "API test generation started"}


@router.get("/api-test-results/{job_id}", response_model=APITestResultsResponse)
async def get_api_test_results(job_id: str, db: Session = Depends(get_db)):
    """Get API test generation results"""
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

    return APITestResultsResponse(
        job_id=job_id,
        summary={
            'total_tests': results.get('total_tests', 0),
            'total_flows': results.get('total_flows', 0),
            'endpoints_covered': results.get('endpoints_covered', 0),
            'output_format': results.get('output_format', 'postman')
        },
        endpoint_coverage=results.get('endpoint_coverage', []),
        category_counts=results.get('categories', {}),
        sample_tests=results.get('sample_tests', []),
        sample_flows=results.get('sample_flows', []),
        spec_info=results.get('spec_info')
    )


@router.get("/download-api-tests/{job_id}")
async def download_api_tests(
    job_id: str,
    type: str = "postman",
    db: Session = Depends(get_db)
):
    """Download API test outputs (postman collection or JSON suite)"""
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatusEnum.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet")

    output_dir = os.path.join("outputs", job_id)

    if type == "json":
        filepath = os.path.join(output_dir, "test_suite.json")
        filename = f"api_test_suite_{job_id[:8]}.json"
    else:
        filepath = os.path.join(output_dir, "postman_collection.json")
        filename = f"postman_collection_{job_id[:8]}.json"

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(filepath, media_type="application/json", filename=filename)
