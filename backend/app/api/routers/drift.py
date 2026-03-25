from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Optional
import os
import tempfile
import pandas as pd

from app.api.models import DriftDetectionResponse, ColumnDriftResult, ConceptDriftResult
from app.utils.file_handler import load_data
from app.services.drift_detector import detect_drift
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/drift-detect", response_model=DriftDetectionResponse)
async def drift_detection(
    baseline: UploadFile = File(...),
    snapshot: UploadFile = File(...),
    target_column: Optional[str] = Form(None)
):
    """Detect distribution drift between baseline and snapshot datasets."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(baseline.filename)[1]) as tmp1:
            content1 = await baseline.read()
            tmp1.write(content1)
            path1 = tmp1.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(snapshot.filename)[1]) as tmp2:
            content2 = await snapshot.read()
            tmp2.write(content2)
            path2 = tmp2.name

        df_baseline = load_data(path1)
        df_snapshot = load_data(path2)

        os.unlink(path1)
        os.unlink(path2)

        if target_column:
            if target_column not in df_baseline.columns:
                raise HTTPException(
                    status_code=400,
                    detail=f"Target column '{target_column}' not found in baseline dataset. "
                           f"Available columns: {list(df_baseline.columns)}"
                )
            if target_column not in df_snapshot.columns:
                raise HTTPException(
                    status_code=400,
                    detail=f"Target column '{target_column}' not found in snapshot dataset."
                )

        results = detect_drift(df_baseline, df_snapshot, target_column=target_column)

        concept_drift_response = None
        if results.get("concept_drift") and not results["concept_drift"].get("error"):
            concept_drift_response = ConceptDriftResult(**results["concept_drift"])

        return DriftDetectionResponse(
            overall_drift_score=results["overall_drift_score"],
            columns=[ColumnDriftResult(**c) for c in results["columns"]],
            summary=results["summary"],
            alert_counts=results["alert_counts"],
            concept_drift=concept_drift_response
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drift-columns")
async def get_drift_columns(
    file: UploadFile = File(...)
):
    """Read a CSV/XLSX file header and return column names for target selection."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            content = await file.read()
            tmp.write(content)
            path = tmp.name

        df = load_data(path)
        os.unlink(path)

        columns = []
        for col in df.columns:
            col_type = "numeric" if pd.api.types.is_numeric_dtype(df[col]) else "categorical"
            columns.append({"name": col, "type": col_type})

        return {"columns": columns}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
