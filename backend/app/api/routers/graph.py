from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import json
import uuid

from app.api.models import GenerateRequest, GraphUploadResponse, GraphStatsInfo, GraphResultsResponse
from app.db.database import get_db, Job, JobStatusEnum
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/upload-graph", response_model=GraphUploadResponse)
async def upload_graph(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a graph file for synthesis"""
    allowed_extensions = ['.csv', '.json', '.graphml', '.gexf']
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

        from app.services.graph_synthesizer import GraphAnalyzer
        G = GraphAnalyzer.load_graph(filepath)
        stats = GraphAnalyzer.analyze_graph(G)

        job = Job(
            id=job_id,
            filename=file.filename,
            original_path=filepath,
            status=JobStatusEnum.PENDING,
            rows_original=stats.get('nodes', 0),
            columns=stats.get('edges', 0)
        )
        db.add(job)
        db.commit()

        return GraphUploadResponse(
            job_id=job_id,
            filename=file.filename,
            graph_stats=GraphStatsInfo(
                nodes=stats.get('nodes', 0),
                edges=stats.get('edges', 0),
                density=stats.get('density', 0),
                avg_degree=stats.get('avg_degree', 0),
                clustering_coefficient=stats.get('clustering_coefficient', 0),
                connected_components=stats.get('connected_components', 0),
                is_directed=stats.get('is_directed', False)
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-graph")
async def generate_graph(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start synthetic graph generation"""
    job = db.query(Job).filter(Job.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatusEnum.PENDING:
        raise HTTPException(status_code=400, detail="Job already processing or completed")

    job.model_type = 'graph_synth'
    job.status = JobStatusEnum.PROCESSING
    job.message = "Starting graph synthesis..."
    job.config_json = json.dumps(request.config.dict())
    db.commit()

    from app.services.graph_synthesizer import generate_graph_background
    background_tasks.add_task(
        generate_graph_background,
        job_id=request.job_id,
        original_path=job.original_path,
        config=request.config.dict()
    )

    return {"job_id": request.job_id, "status": "processing", "message": "Graph synthesis started"}


@router.get("/graph-results/{job_id}", response_model=GraphResultsResponse)
async def get_graph_results(job_id: str, db: Session = Depends(get_db)):
    """Get graph synthesis results"""
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

    return GraphResultsResponse(
        job_id=job_id,
        summary=results.get('summary', {}),
        original_stats=results.get('original_stats', {}),
        synthetic_stats=results.get('synthetic_stats', {}),
        comparison=results.get('comparison', {}),
        graph_data=results.get('graph_data'),
    )


@router.get("/download-graph/{job_id}")
async def download_graph(job_id: str, db: Session = Depends(get_db)):
    """Download synthetic graph"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatusEnum.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet")

    output_dir = os.path.join("outputs", job_id)
    for prefix in ['augmented_graph', 'synthetic_graph']:
        for ext in ['.csv', '.json', '.graphml', '.gexf']:
            filepath = os.path.join(output_dir, f"{prefix}{ext}")
            if os.path.exists(filepath):
                media_types = {'.csv': 'text/csv', '.json': 'application/json', '.graphml': 'application/xml', '.gexf': 'application/xml'}
                return FileResponse(
                    filepath,
                    media_type=media_types.get(ext, 'application/octet-stream'),
                    filename=f"{prefix}_{job_id[:8]}{ext}"
                )

    raise HTTPException(status_code=404, detail="Graph file not found")
