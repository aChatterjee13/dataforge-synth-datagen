"""
Adapter for DGAN (DoppelGANger) time-series generation via gretel-synthetics.
Uses lazy imports to avoid loading heavy dependencies at startup.
Falls back to TimeGAN on ImportError.
"""

import pandas as pd
import numpy as np
from typing import Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


def generate_dgan_synthetic(
    df: pd.DataFrame,
    n_samples: int,
    datetime_col: Optional[str] = None,
    epochs: int = 300,
) -> pd.DataFrame:
    """
    Generate synthetic time-series data using DGAN (DoppelGANger).

    Args:
        df: Original DataFrame with time-series data
        n_samples: Number of synthetic samples to generate
        datetime_col: Name of the datetime column (excluded from training)
        epochs: Training epochs

    Returns:
        pd.DataFrame of synthetic data
    """
    try:
        from gretel_synthetics.timeseries_dgan.dgan import DGAN
        from gretel_synthetics.timeseries_dgan.config import DGANConfig

        work_df = df.copy()

        # Separate datetime column if present
        datetime_values = None
        if datetime_col and datetime_col in work_df.columns:
            datetime_values = work_df[datetime_col]
            work_df = work_df.drop(columns=[datetime_col])

        # Separate numeric (features) from non-numeric (attributes)
        numeric_cols = work_df.select_dtypes(include=[np.number]).columns.tolist()
        non_numeric_cols = work_df.select_dtypes(exclude=[np.number]).columns.tolist()

        if not numeric_cols:
            raise ValueError("DGAN requires at least one numeric column for features")

        # Prepare features array: shape (n_examples, seq_len, n_features)
        # For non-sequential data, treat each row as a sequence of length 1
        features = work_df[numeric_cols].values.astype(np.float32)
        seq_len = min(24, len(features))
        n_examples = len(features) // seq_len
        features = features[:n_examples * seq_len].reshape(n_examples, seq_len, len(numeric_cols))

        # Prepare attributes if we have non-numeric columns
        attributes = None
        if non_numeric_cols:
            # Encode categorical attributes as numeric
            attr_df = work_df[non_numeric_cols].copy()
            for col in non_numeric_cols:
                attr_df[col] = pd.Categorical(attr_df[col]).codes.astype(np.float32)
            attributes = attr_df.values[:n_examples].astype(np.float32)

        config = DGANConfig(
            max_sequence_len=seq_len,
            sample_len=min(seq_len, 5),
            epochs=epochs,
        )

        model = DGAN(config)
        model.train_numpy(features=features, attributes=attributes)

        # Generate synthetic data
        n_gen = max(1, n_samples // seq_len)
        synth_attributes, synth_features = model.generate_numpy(n_gen)

        # Reshape features back to 2D
        synth_flat = synth_features.reshape(-1, len(numeric_cols))[:n_samples]
        result_df = pd.DataFrame(synth_flat, columns=numeric_cols)

        # Re-add non-numeric columns with sampled values from original
        for col in non_numeric_cols:
            result_df[col] = np.random.choice(work_df[col].values, size=len(result_df))

        # Re-add datetime column with generated timestamps
        if datetime_col and datetime_values is not None:
            result_df[datetime_col] = pd.date_range(
                start=datetime_values.min(),
                periods=len(result_df),
                freq=pd.infer_freq(datetime_values.head(10)) or 'h'
            )

        # Restore original column order
        original_cols = [c for c in df.columns if c in result_df.columns]
        result_df = result_df[original_cols]

        logger.info(f"DGAN: Generated {len(result_df)} rows")
        return result_df

    except ImportError as e:
        logger.warning(f"gretel-synthetics not available ({e}), falling back to TimeGAN")
        raise
    except Exception as e:
        logger.error(f"DGAN failed: {e}")
        raise
