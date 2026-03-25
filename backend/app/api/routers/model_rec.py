from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import pandas as pd

from app.api.models import ModelRecommendation
from app.db.database import get_db, Job
from app.utils.file_handler import load_data
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/recommend/{job_id}", response_model=ModelRecommendation)
async def get_model_recommendation(job_id: str, use_case: str = "ml_training", db: Session = Depends(get_db)):
    """Get model recommendation for a job based on dataset analysis and use case"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        df = load_data(job.original_path)
        num_rows, num_cols = df.shape
        reasons = []
        alternatives = []

        # Analyze dataset
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(exclude=['number']).columns.tolist()
        has_datetime = any(pd.api.types.is_datetime64_any_dtype(df[c]) for c in df.columns)

        # Check for time-series
        from app.services.timegan import TimeSeriesDetector
        ts_detection = TimeSeriesDetector.detect_time_series(df)
        is_timeseries = ts_detection.get('is_time_series', False) and ts_detection.get('confidence', 0) > 0.5

        recommended = "auto"
        confidence = 0.7

        if use_case == "prototyping":
            recommended = "llm_row_gen"
            confidence = 0.9
            reasons.append("Prototyping use case — LLM generates semantically coherent data fast")
            reasons.append("No model training needed, results in seconds via API")
            alternatives.append({"model": "gaussian_copula", "reason": "Statistical model if you need distribution fidelity"})
            alternatives.append({"model": "ctgan", "reason": "Better statistical properties but slower"})

        elif is_timeseries:
            recommended = "timegan"
            confidence = 0.9
            reasons.append(f"Time-series patterns detected (confidence: {ts_detection['confidence']:.0%})")
            reasons.append(f"Found datetime columns: {', '.join(ts_detection.get('datetime_columns', []))}")
            alternatives.append({"model": "dgan", "reason": "DoppelGANger — better for large time-series with metadata"})
            alternatives.append({"model": "ctgan", "reason": "Good for tabular data if temporal patterns aren't critical"})

        elif num_rows >= 5000:
            recommended = "tab_ddpm"
            confidence = 0.85
            reasons.append(f"Large dataset ({num_rows} rows) — TabDDPM is state-of-the-art for quality")
            reasons.append("Diffusion models produce the highest fidelity synthetic data")
            alternatives.append({"model": "ctgan", "reason": "Faster training, proven reliability"})
            alternatives.append({"model": "ctab_gan_plus", "reason": "Optimized for ML utility"})
            alternatives.append({"model": "dp_ctgan", "reason": "If privacy is a primary concern"})

        elif num_rows < 500:
            recommended = "gaussian_copula"
            confidence = 0.85
            reasons.append(f"Small dataset ({num_rows} rows) — GaussianCopula is fastest and works well")
            reasons.append("Training will complete in seconds")
            alternatives.append({"model": "bayesian_network", "reason": "Interpretable, captures causal relationships"})
            alternatives.append({"model": "ctgan", "reason": "Better for complex distributions but slower"})

        elif len(categorical_cols) > len(numeric_cols):
            recommended = "ctgan"
            confidence = 0.85
            reasons.append(f"Mixed data types with {len(categorical_cols)} categorical columns")
            reasons.append("CTGAN handles categorical distributions well")
            alternatives.append({"model": "tvae", "reason": "Also good for mixed data, sometimes faster"})
            alternatives.append({"model": "ctab_gan_plus", "reason": "Optimized for downstream ML utility"})

        else:
            recommended = "ctgan"
            confidence = 0.8
            reasons.append(f"Dataset has {num_rows} rows and {num_cols} columns")
            reasons.append("CTGAN provides best quality for medium-to-large datasets")
            alternatives.append({"model": "gaussian_copula", "reason": "Faster training, good for simpler distributions"})
            alternatives.append({"model": "tvae", "reason": "Good alternative for mixed data types"})
            alternatives.append({"model": "tab_ddpm", "reason": "State-of-the-art quality (slower training)"})

        # Always include DP-CTGAN in alternatives if not already recommended
        if recommended != "dp_ctgan" and use_case == "ml_training":
            has_dp = any(a["model"] == "dp_ctgan" for a in alternatives)
            if not has_dp:
                alternatives.append({"model": "dp_ctgan", "reason": "Differential privacy baked into training"})

        dataset_summary = {
            "rows": num_rows,
            "columns": num_cols,
            "numeric_columns": len(numeric_cols),
            "categorical_columns": len(categorical_cols),
            "has_datetime": has_datetime,
            "is_timeseries": is_timeseries,
        }

        return ModelRecommendation(
            recommended_model=recommended,
            confidence=confidence,
            reasons=reasons,
            alternatives=alternatives,
            dataset_summary=dataset_summary
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
