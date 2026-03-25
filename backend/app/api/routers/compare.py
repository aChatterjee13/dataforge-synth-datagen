from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import tempfile

from app.api.models import ValidationResponse
from app.utils.file_handler import load_data
from app.services.validator import validate_synthetic_data
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/compare", response_model=ValidationResponse)
async def compare_datasets(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
):
    """Compare two datasets using validation metrics"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file1.filename)[1]) as tmp1:
            content1 = await file1.read()
            tmp1.write(content1)
            path1 = tmp1.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file2.filename)[1]) as tmp2:
            content2 = await file2.read()
            tmp2.write(content2)
            path2 = tmp2.name

        df1 = load_data(path1)
        df2 = load_data(path2)

        os.unlink(path1)
        os.unlink(path2)

        validation_results = validate_synthetic_data(df1, df2)

        return ValidationResponse(
            job_id="compare",
            metrics=validation_results["metrics"],
            assessment_summary=validation_results["assessment_summary"],
            charts=validation_results["charts"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
