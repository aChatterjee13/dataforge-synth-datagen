"""
Unified adapter for synthcity models: TabDDPM, CTAB-GAN+, Bayesian Network.
Uses lazy imports to avoid loading heavy dependencies at startup.
Falls back to CTGAN/GaussianCopula on ImportError.
"""

import pandas as pd
from typing import Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


def generate_synthcity_model(
    df: pd.DataFrame,
    model_name: str,
    num_rows: int,
    epochs: int = 300,
) -> pd.DataFrame:
    """
    Generate synthetic data using a synthcity model.

    Args:
        df: Original DataFrame to learn from
        model_name: One of "ddpm", "ctabgan", "bayesian_network"
        num_rows: Number of synthetic rows to generate
        epochs: Training epochs (ignored for bayesian_network)

    Returns:
        pd.DataFrame of synthetic data
    """
    try:
        from synthcity.plugins import Plugins
        from synthcity.plugins.core.dataloader import GenericDataLoader

        loader = GenericDataLoader(df)

        plugin_kwargs = {}
        if model_name in ("ddpm", "ctabgan"):
            plugin_kwargs["n_iter"] = epochs

        plugin = Plugins().get(model_name, **plugin_kwargs)
        plugin.fit(loader)

        synthetic_loader = plugin.generate(count=num_rows)
        synthetic_df = synthetic_loader.dataframe()

        # Ensure column order matches original
        synthetic_df = synthetic_df[df.columns.intersection(synthetic_df.columns)]

        logger.info(f"synthcity ({model_name}): Generated {len(synthetic_df)} rows")
        return synthetic_df

    except ImportError as e:
        logger.warning(f"synthcity not available ({e}), falling back to CTGAN")
        raise
    except Exception as e:
        logger.error(f"synthcity ({model_name}) failed: {e}")
        raise
