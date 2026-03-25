from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import os
import json
import uuid
import zipfile
from io import BytesIO

from app.api.models import UploadResponse, GenerateRequest, DataType, PDFInfo
from app.db.database import get_db, Job, JobStatusEnum, SessionLocal
from app.services.pdf_generator import PDFExtractor, generate_synthetic_pdfs_from_samples
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/upload-pdfs", response_model=UploadResponse)
async def upload_pdfs(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Upload PDF files for synthetic PDF generation"""
    for file in files:
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension != '.pdf':
            raise HTTPException(
                status_code=400,
                detail=f"Only PDF files allowed. Found: {file.filename}"
            )

    try:
        job_id = str(uuid.uuid4())

        upload_dir = os.path.join("uploads", job_id, "sample_pdfs")
        os.makedirs(upload_dir, exist_ok=True)

        pdf_infos = []
        total_pages = 0
        total_words = 0

        extractor = PDFExtractor()

        for file in files:
            file_path = os.path.join(upload_dir, file.filename)
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)

            analysis = extractor.analyze_pdf_structure(file_path)

            if analysis.get('success'):
                pdf_info = PDFInfo(
                    total_pages=analysis['total_pages'],
                    total_words=analysis['total_words'],
                    content_type=analysis['analysis']['content_type'],
                    avg_words_per_page=analysis['analysis']['avg_words_per_page']
                )
                pdf_infos.append(pdf_info)
                total_pages += analysis['total_pages']
                total_words += analysis['total_words']

        job = Job(
            id=job_id,
            filename=f"{len(files)} PDF(s)",
            original_path=upload_dir,
            status=JobStatusEnum.PENDING,
            rows_original=len(files),
            columns=0
        )
        db.add(job)
        db.commit()

        return UploadResponse(
            job_id=job_id,
            filename=f"{len(files)} PDF files uploaded",
            rows=0,
            columns=0,
            column_types={},
            data_type=DataType.UNSTRUCTURED,
            pdf_count=len(files),
            pdf_info=pdf_infos,
            message=f"Successfully uploaded {len(files)} PDF(s) - {total_pages} pages, {total_words} words"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-pdfs")
async def generate_pdfs(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start synthetic PDF generation using GPT"""
    try:
        logger.info(f"PDF Generation Request - Job ID: {request.job_id}")

        job = db.query(Job).filter(Job.id == request.job_id).first()

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status != JobStatusEnum.PENDING:
            raise HTTPException(status_code=400, detail="Job already processing or completed")

        config = request.config

        logger.debug(f"GPT API Key from config: {'<set>' if config.gpt_api_key else '<not set>'}")
        logger.debug(f"GPT API Key from env: {'<set>' if os.getenv('OPENAI_API_KEY') else '<not set>'}")

        if not config.gpt_api_key and not os.getenv('OPENAI_API_KEY'):
            raise HTTPException(
                status_code=400,
                detail="GPT API key not provided. Set OPENAI_API_KEY environment variable or provide gpt_api_key in config"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generate_pdfs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    try:
        job.model_type = config.model_type.value if hasattr(config.model_type, 'value') else str(config.model_type)
    except Exception as e:
        logger.warning(f"Error setting model_type: {e}, using default")
        job.model_type = 'gpt_pdf'

    job.num_rows = config.num_pdfs
    job.status = JobStatusEnum.PROCESSING
    job.message = "Starting PDF generation..."

    try:
        job.config_json = json.dumps(config.dict())
    except Exception as e:
        logger.warning(f"Error serializing config: {e}")
        job.config_json = json.dumps({
            'model_type': str(config.model_type),
            'num_pdfs': config.num_pdfs,
            'gpt_model': config.gpt_model
        })

    db.commit()

    background_tasks.add_task(
        _generate_pdfs_background,
        job_id=request.job_id,
        sample_pdf_folder=job.original_path,
        config=config
    )

    return {
        "job_id": request.job_id,
        "status": "processing",
        "message": "PDF generation started"
    }


def _generate_pdfs_background(job_id: str, sample_pdf_folder: str, config):
    """Background task for PDF generation"""
    from dotenv import load_dotenv
    load_dotenv()

    db = SessionLocal()

    try:
        job = db.query(Job).filter(Job.id == job_id).first()

        if not job:
            logger.error(f"Job {job_id} not found")
            return

        output_folder = os.path.join("outputs", job_id)
        os.makedirs(output_folder, exist_ok=True)

        def update_progress(progress: float, message: str):
            job.progress = int(progress)
            job.message = message
            db.commit()

        api_key = config.gpt_api_key if config.gpt_api_key else os.getenv('OPENAI_API_KEY')

        logger.info(f"Using API key: {api_key[:20]}..." if api_key else "No API key found")

        results = generate_synthetic_pdfs_from_samples(
            sample_pdf_folder=sample_pdf_folder,
            output_folder=output_folder,
            num_pdfs_per_sample=config.num_pdfs,
            gpt_api_key=api_key,
            gpt_endpoint=config.gpt_endpoint,
            progress_callback=update_progress
        )

        if results['success']:
            job.status = JobStatusEnum.COMPLETED
            job.progress = 100
            job.message = f"Generated {results['pdfs_generated']} PDF(s) successfully"
            job.rows_generated = results['pdfs_generated']
            job.original_path = output_folder
        else:
            job.status = JobStatusEnum.FAILED
            job.error = results.get('error', 'Unknown error')
            job.message = f"PDF generation failed: {job.error}"

        db.commit()

    except Exception as e:
        logger.error(f"Error in PDF generation: {e}", exc_info=True)
        if job:
            job.status = JobStatusEnum.FAILED
            job.error = str(e)
            job.message = f"Error: {str(e)}"
            db.commit()
    finally:
        db.close()


@router.get("/download-pdf/{job_id}/{filename}")
async def download_pdf(
    job_id: str,
    filename: str,
    db: Session = Depends(get_db)
):
    """Download a specific generated PDF"""
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatusEnum.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet")

    pdf_path = os.path.join(job.original_path, filename)

    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=filename
    )


@router.get("/download-pdfs-zip/{job_id}")
async def download_pdfs_zip(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Download all generated PDFs as a ZIP file"""
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatusEnum.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet")

    output_folder = job.original_path

    if not os.path.exists(output_folder):
        raise HTTPException(status_code=404, detail="Output folder not found")

    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename in os.listdir(output_folder):
            if filename.endswith('.pdf'):
                file_path = os.path.join(output_folder, filename)
                zip_file.write(file_path, filename)

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=synthetic_pdfs_{job_id}.zip"}
    )


@router.get("/list-pdfs/{job_id}")
async def list_generated_pdfs(
    job_id: str,
    db: Session = Depends(get_db)
):
    """List all generated PDFs for a job"""
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatusEnum.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet")

    output_folder = job.original_path

    if not os.path.exists(output_folder):
        raise HTTPException(status_code=404, detail="Output folder not found")

    pdfs = []
    for filename in os.listdir(output_folder):
        if filename.endswith('.pdf'):
            file_path = os.path.join(output_folder, filename)
            file_size = os.path.getsize(file_path)

            pdfs.append({
                'filename': filename,
                'size': file_size,
                'download_url': f"/api/download-pdf/{job_id}/{filename}"
            })

    return {
        'job_id': job_id,
        'total_pdfs': len(pdfs),
        'pdfs': pdfs
    }
