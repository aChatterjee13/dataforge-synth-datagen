"""
Adapter for REaLTabFormer (GPT-2 based tabular data generation).
Uses lazy imports to avoid loading heavy dependencies at startup.
Falls back to CTGAN on ImportError.
"""

import pandas as pd
from typing import Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


def generate_realtabformer_synthetic(
    df: pd.DataFrame,
    num_rows: int,
    epochs: int = 100,
) -> pd.DataFrame:
    """
    Generate synthetic data using REaLTabFormer.

    Args:
        df: Original DataFrame to learn from
        num_rows: Number of synthetic rows to generate
        epochs: Training epochs

    Returns:
        pd.DataFrame of synthetic data
    """
    try:
        from realtabformer import REaLTabFormer

        model = REaLTabFormer(model_type="tabular", epochs=epochs)
        model.fit(df)

        synthetic_df = model.sample(n_samples=num_rows)

        # Ensure column order matches original
        synthetic_df = synthetic_df[df.columns.intersection(synthetic_df.columns)]

        logger.info(f"REaLTabFormer: Generated {len(synthetic_df)} rows")
        return synthetic_df

    except ImportError as e:
        logger.warning(f"realtabformer not available ({e}), falling back to CTGAN")
        raise
    except Exception as e:
        logger.error(f"REaLTabFormer failed: {e}")
        raise
