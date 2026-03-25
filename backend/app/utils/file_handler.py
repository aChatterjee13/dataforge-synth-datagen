import pandas as pd
import os
from typing import Tuple, Dict
import uuid

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"

def save_upload_file(file, filename: str) -> Tuple[str, str]:
    """Save uploaded file and return job_id and file path"""
    job_id = str(uuid.uuid4())
    file_extension = os.path.splitext(filename)[1]
    filepath = os.path.join(UPLOAD_DIR, f"{job_id}{file_extension}")

    # Save file
    with open(filepath, "wb") as f:
        f.write(file.read())

    return job_id, filepath

def load_data(filepath: str) -> pd.DataFrame:
    """Load data from file path"""
    file_extension = os.path.splitext(filepath)[1].lower()

    if file_extension == '.csv':
        return pd.read_csv(filepath)
    elif file_extension in ['.xlsx', '.xls']:
        return pd.read_excel(filepath)
    else:
        raise ValueError(f"Unsupported file format: {file_extension}")

def analyze_dataframe(df: pd.DataFrame) -> Dict:
    """Analyze dataframe and return metadata including potential target variables"""
    from app.services.timegan import TimeSeriesDetector

    column_types = {}
    potential_targets = {
        "classification": [],
        "regression": []
    }

    # Detect time-series characteristics
    ts_detection = TimeSeriesDetector.detect_time_series(df)
    is_timeseries = ts_detection.get('is_time_series', False)
    datetime_cols = ts_detection.get('datetime_columns', [])

    for col in df.columns:
        dtype = df[col].dtype
        nunique = df[col].nunique()
        null_pct = df[col].isnull().sum() / len(df) * 100

        # Basic type detection
        if pd.api.types.is_numeric_dtype(dtype):
            if pd.api.types.is_integer_dtype(dtype):
                column_types[col] = "integer"
            else:
                column_types[col] = "float"
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            column_types[col] = "datetime"
        elif pd.api.types.is_bool_dtype(dtype):
            column_types[col] = "boolean"
        else:
            # Check if it's categorical (few unique values)
            if nunique < 20 and len(df) > 100:
                column_types[col] = "categorical"
            else:
                column_types[col] = "text"

        # Detect potential target variables for ML efficacy testing
        # Skip if too many nulls or if it's an ID column
        if null_pct > 30 or nunique / len(df) > 0.95:
            continue

        # Detect classification targets (categorical or binary)
        if column_types[col] == "categorical" or (column_types[col] in ["integer", "boolean"] and nunique <= 20):
            # Good for classification if 2-20 unique values
            if 2 <= nunique <= 20:
                potential_targets["classification"].append({
                    "name": col,
                    "type": column_types[col],
                    "unique_values": int(nunique),
                    "null_percentage": round(null_pct, 2),
                    "reason": f"Binary classification" if nunique == 2 else f"Multi-class ({nunique} classes)"
                })

        # Detect regression targets (continuous numeric)
        if column_types[col] in ["float", "integer"] and nunique > 20:
            # Good for regression if continuous with many unique values
            potential_targets["regression"].append({
                "name": col,
                "type": column_types[col],
                "unique_values": int(nunique),
                "null_percentage": round(null_pct, 2),
                "reason": "Continuous numeric variable"
            })

    # Sort by most likely targets (fewer nulls, good cardinality)
    potential_targets["classification"].sort(key=lambda x: (x["null_percentage"], -x["unique_values"]))
    potential_targets["regression"].sort(key=lambda x: x["null_percentage"])

    return {
        "rows": len(df),
        "columns": len(df.columns),
        "column_types": column_types,
        "column_names": list(df.columns),
        "potential_targets": potential_targets,
        "is_timeseries": is_timeseries,
        "timeseries_info": {
            "datetime_columns": datetime_cols,
            "confidence": ts_detection.get('confidence', 0.0),
            "temporal_features": ts_detection.get('temporal_features', []),
            "suggested_datetime_col": datetime_cols[0] if datetime_cols else None
        } if is_timeseries else None
    }

def save_synthetic_data(df: pd.DataFrame, job_id: str) -> str:
    """Save synthetic dataframe and return path"""
    filepath = os.path.join(OUTPUT_DIR, f"{job_id}_synthetic.csv")
    df.to_csv(filepath, index=False)
    return filepath

def get_output_path(job_id: str) -> str:
    """Get output file path for a job"""
    return os.path.join(OUTPUT_DIR, f"{job_id}_synthetic.csv")
