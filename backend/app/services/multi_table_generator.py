"""
Multi-Table Relational Synthesis Service (Feature 9)
Uses SDV's HMASynthesizer to generate synthetic data preserving referential integrity.
"""
import pandas as pd
from typing import Dict, List, Any, Callable, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


def generate_multi_table_synthetic(
    tables: Dict[str, pd.DataFrame],
    relationships: List[Dict[str, str]],
    num_rows: int = 1000,
    epochs: int = 300,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Dict[str, pd.DataFrame]:
    """
    Generate synthetic data for multiple related tables.

    Args:
        tables: Dict mapping table names to DataFrames
        relationships: List of dicts with parent_table, parent_column, child_table, child_column
        num_rows: Number of rows to generate per table
        epochs: Training epochs
        progress_callback: Optional callback for progress updates

    Returns:
        Dict mapping table names to synthetic DataFrames
    """
    from sdv.metadata import MultiTableMetadata
    from sdv.multi_table import HMASynthesizer

    if progress_callback:
        progress_callback(10.0, "Building multi-table metadata...")

    # Build metadata
    metadata = MultiTableMetadata()

    for table_name, df in tables.items():
        metadata.detect_table_from_dataframe(table_name, df)

    if progress_callback:
        progress_callback(20.0, "Configuring table relationships...")

    # Add relationships
    for rel in relationships:
        try:
            metadata.add_relationship(
                parent_table_name=rel["parent_table"],
                parent_primary_key=rel["parent_column"],
                child_table_name=rel["child_table"],
                child_foreign_key=rel["child_column"]
            )
        except Exception as e:
            logger.warning(f"Could not add relationship {rel}: {e}")

    if progress_callback:
        progress_callback(30.0, "Training HMA Synthesizer...")

    # Create and train synthesizer
    synthesizer = HMASynthesizer(metadata)
    synthesizer.fit(tables)

    if progress_callback:
        progress_callback(80.0, "Generating synthetic tables...")

    # Generate synthetic data
    # HMA generates proportionally; we scale if needed
    synthetic_tables = synthesizer.sample(scale=max(1, num_rows // max(len(df) for df in tables.values())))

    if progress_callback:
        progress_callback(95.0, "Multi-table generation complete")

    return synthetic_tables


def analyze_multi_table_upload(
    tables: Dict[str, pd.DataFrame]
) -> Dict[str, Dict[str, Any]]:
    """
    Analyze uploaded tables and return summary information.
    """
    result = {}
    for name, df in tables.items():
        column_types = {}
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                column_types[col] = "numeric"
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                column_types[col] = "datetime"
            else:
                column_types[col] = "categorical"

        result[name] = {
            "rows": len(df),
            "columns": len(df.columns),
            "column_types": column_types
        }
    return result
