# CRITICAL: Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv()  # Load .env file

# CRITICAL: Set TensorFlow environment variables BEFORE any imports
# This fixes macOS TensorFlow mutex deadlock issues
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['TF_NUM_INTEROP_THREADS'] = '1'
os.environ['TF_NUM_INTRAOP_THREADS'] = '1'

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.middleware import RequestTrackingMiddleware
from app.middleware.auth import verify_api_key
from app.utils.logger import setup_logging, get_logger

# Setup centralized logging
setup_logging(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    log_file='logs/dataforge.log',
    json_format=False  # Set to True for JSON structured logs
)

logger = get_logger(__name__)

app = FastAPI(
    title="DataForge API",
    description="Synthetic Data Generation Platform",
    version="1.0.0"
)

# Add request tracking middleware FIRST (order matters!)
app.add_middleware(RequestTrackingMiddleware)

# Upload size limit middleware
MAX_UPLOAD_SIZE = int(os.getenv('MAX_UPLOAD_SIZE', str(100 * 1024 * 1024)))  # 100MB default

class UploadSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > MAX_UPLOAD_SIZE:
            return JSONResponse(status_code=413, content={"detail": "File too large"})
        return await call_next(request)

app.add_middleware(UploadSizeLimitMiddleware)

# CORS middleware
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("DataForge API starting up...")

# Create directories if they don't exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

# Include all domain routers with auth dependency
from app.api.routers import (
    core, compare, presets, model_rec, api_keys, multi_table,
    conditional, drift, streaming, pdf, api_testing, db_testing,
    pii, logs, cdc, graph,
)

_all_routers = [
    core.router, compare.router, presets.router, model_rec.router,
    api_keys.router, multi_table.router, conditional.router, drift.router,
    streaming.router, pdf.router, api_testing.router, db_testing.router,
    pii.router, logs.router, cdc.router, graph.router,
]

for r in _all_routers:
    app.include_router(r, prefix="/api", dependencies=[Depends(verify_api_key)])

@app.get("/")
async def root():
    return {
        "message": "DataForge API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health():
    from app.db.database import engine
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "database": "disconnected"})
