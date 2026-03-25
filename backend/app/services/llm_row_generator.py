"""
LLM-based row generator for prototyping/demo use cases.
Uses the existing LLMClient to generate semantically coherent tabular rows.
"""

import pandas as pd
import json
from typing import Optional, Callable

from app.utils.logger import get_logger

logger = get_logger(__name__)


def generate_llm_rows(
    df: pd.DataFrame,
    num_rows: int,
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
    endpoint: Optional[str] = None,
    batch_size: int = 50,
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> pd.DataFrame:
    """
    Generate synthetic rows using an LLM (GPT) API.

    Builds a schema description + 10 sample rows, sends to LLM,
    and parses the JSON array response. Generates in batches.

    Args:
        df: Original DataFrame to learn schema and patterns from
        num_rows: Total number of rows to generate
        api_key: OpenAI API key (falls back to env var)
        model: LLM model name
        endpoint: Custom API endpoint
        batch_size: Rows per API call
        progress_callback: Optional (progress_pct, message) callback

    Returns:
        pd.DataFrame of synthetic data
    """
    from app.services.llm_client import LLMClient

    client_kwargs = {"model": model}
    if api_key:
        client_kwargs["api_key"] = api_key
    if endpoint:
        client_kwargs["api_endpoint"] = endpoint

    client = LLMClient(**client_kwargs)

    # Build schema description
    schema_lines = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        nunique = df[col].nunique()
        sample_vals = df[col].dropna().head(5).tolist()
        schema_lines.append(
            f"  - {col} ({dtype}, {nunique} unique values, examples: {sample_vals})"
        )
    schema_str = "\n".join(schema_lines)

    # Get 10 sample rows as JSON
    sample_rows = df.head(10).to_dict(orient="records")
    sample_json = json.dumps(sample_rows, default=str, indent=2)

    system_prompt = (
        "You are a synthetic data generator. Given a table schema and sample rows, "
        "generate new realistic rows that follow the same patterns, distributions, and "
        "relationships. Output ONLY a JSON array of objects with the exact same column names. "
        "Do not include any explanation, just the JSON array."
    )

    all_rows = []
    generated = 0

    while generated < num_rows:
        current_batch = min(batch_size, num_rows - generated)

        user_prompt = (
            f"Table schema:\n{schema_str}\n\n"
            f"Sample rows:\n{sample_json}\n\n"
            f"Generate exactly {current_batch} new synthetic rows as a JSON array. "
            f"Maintain realistic values, distributions, and relationships between columns."
        )

        try:
            result = client.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                expect_json=True,
            )

            # Handle both list and dict with "rows" key
            if isinstance(result, dict):
                rows = result.get("rows", result.get("data", []))
            elif isinstance(result, list):
                rows = result
            else:
                logger.warning(f"LLM returned unexpected type: {type(result)}")
                continue

            # Filter to only dict items (skip any strings the LLM may return)
            rows = [r for r in rows if isinstance(r, dict)]
            all_rows.extend(rows)
            generated += len(rows)

            if progress_callback:
                pct = min(95.0, 20.0 + (generated / num_rows) * 70.0)
                progress_callback(pct, f"LLM generated {generated}/{num_rows} rows...")

        except Exception as e:
            logger.error(f"LLM batch generation error: {e}")
            if generated > 0:
                break
            raise

    if not all_rows:
        raise RuntimeError("LLM generated zero rows")

    # Build DataFrame and cast dtypes to match original
    synthetic_df = pd.DataFrame(all_rows[:num_rows])

    # Ensure only expected columns are present
    expected_cols = [c for c in df.columns if c in synthetic_df.columns]
    synthetic_df = synthetic_df[expected_cols]

    # Cast dtypes to match original
    for col in expected_cols:
        try:
            if pd.api.types.is_integer_dtype(df[col]):
                synthetic_df[col] = pd.to_numeric(synthetic_df[col], errors="coerce").astype("Int64")
            elif pd.api.types.is_float_dtype(df[col]):
                synthetic_df[col] = pd.to_numeric(synthetic_df[col], errors="coerce")
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                synthetic_df[col] = pd.to_datetime(synthetic_df[col], errors="coerce")
        except Exception:
            pass  # Keep as-is if conversion fails

    logger.info(f"LLM Row Generator: Generated {len(synthetic_df)} rows")
    return synthetic_df
