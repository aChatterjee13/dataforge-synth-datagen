"""
SMOTE oversampling post-processor.
Applies SMOTE to balance class distributions in synthetic data.
Uses lazy imports; returns original DataFrame on failure (graceful degradation).
"""

import pandas as pd
import numpy as np
from typing import Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


def apply_smote(
    df: pd.DataFrame,
    target_column: str,
    strategy: str = "minority",
    k_neighbors: int = 5,
) -> pd.DataFrame:
    """
    Apply SMOTE oversampling to balance classes in the target column.

    Args:
        df: DataFrame to augment
        target_column: Column containing the class labels
        strategy: SMOTE sampling strategy ('minority', 'not minority', 'not majority', 'all')
        k_neighbors: Number of nearest neighbors for SMOTE interpolation

    Returns:
        pd.DataFrame with balanced classes (or original on failure)
    """
    if target_column not in df.columns:
        logger.warning(f"SMOTE: Target column '{target_column}' not found, skipping")
        return df

    try:
        from imblearn.over_sampling import SMOTE

        # Separate target from features
        y = df[target_column].copy()
        X = df.drop(columns=[target_column]).copy()

        # Identify numeric and non-numeric columns
        numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
        non_numeric_cols = X.select_dtypes(exclude=[np.number]).columns.tolist()

        if not numeric_cols:
            logger.warning("SMOTE: No numeric features found, skipping")
            return df

        # Store non-numeric columns and drop them for SMOTE
        non_numeric_data = X[non_numeric_cols].copy() if non_numeric_cols else None
        X_numeric = X[numeric_cols].copy()

        # Encode target if non-numeric
        target_is_numeric = pd.api.types.is_numeric_dtype(y)
        if not target_is_numeric:
            y_encoded = pd.Categorical(y).codes
            y_categories = pd.Categorical(y).categories
        else:
            y_encoded = y

        # Adjust k_neighbors if needed (must be < smallest class count)
        min_class_count = pd.Series(y_encoded).value_counts().min()
        effective_k = min(k_neighbors, min_class_count - 1)
        if effective_k < 1:
            logger.warning(f"SMOTE: Smallest class has only {min_class_count} samples, skipping")
            return df

        smote = SMOTE(
            sampling_strategy=strategy,
            k_neighbors=effective_k,
            random_state=42,
        )

        X_resampled, y_resampled = smote.fit_resample(X_numeric, y_encoded)

        # Build result DataFrame
        result_df = pd.DataFrame(X_resampled, columns=numeric_cols)

        # Decode target back if needed
        if not target_is_numeric:
            result_df[target_column] = y_categories[y_resampled]
        else:
            result_df[target_column] = y_resampled

        # Re-add non-numeric columns by sampling from original values
        if non_numeric_data is not None and len(non_numeric_cols) > 0:
            for col in non_numeric_cols:
                result_df[col] = np.random.choice(
                    non_numeric_data[col].values,
                    size=len(result_df),
                )

        # Restore original column order
        original_cols = [c for c in df.columns if c in result_df.columns]
        result_df = result_df[original_cols]

        logger.info(f"SMOTE: Augmented from {len(df)} to {len(result_df)} rows "
              f"(target: {target_column}, strategy: {strategy})")
        return result_df

    except ImportError as e:
        logger.warning(f"imbalanced-learn not available ({e}), skipping SMOTE")
        return df
    except Exception as e:
        logger.error(f"SMOTE failed: {e}, returning original data")
        return df
