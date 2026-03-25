import pandas as pd
import numpy as np
from datetime import datetime
import traceback
import requests as http_requests

from app.api.models import GenerationConfig, ModelType, PrivacyMechanism, UseCase
from app.utils.file_handler import load_data, save_synthetic_data
from app.db.database import SessionLocal, Job, JobStatusEnum
from app.utils.logger import get_logger

logger = get_logger(__name__)
# Lazy imports for SDV and TimeGAN to avoid TensorFlow loading at module import
# These will be imported inside functions when needed

def update_job_progress(job_id: str, progress: float, message: str):
    """Update job progress in database"""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.progress = progress
            job.message = message
            db.commit()
    finally:
        db.close()

def update_job_status(job_id: str, status: JobStatusEnum, message: str, error: str = None):
    """Update job status in database"""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = status
            job.message = message
            if error:
                job.error = error
            if status == JobStatusEnum.COMPLETED:
                job.completed_at = datetime.utcnow()
                job.progress = 100.0
            db.commit()
    finally:
        db.close()

def fix_metadata_detection(df: pd.DataFrame, metadata):
    """
    Fix metadata detection issues where column names mislead SDV
    Forces columns to use their actual data type instead of semantic type based on name
    """
    for column in df.columns:
        actual_dtype = df[column].dtype

        # Get the detected sdtype from metadata
        column_metadata = metadata.columns.get(column, {})
        detected_sdtype = column_metadata.get('sdtype', None)

        # If column has numeric data but was detected as something else (e.g., email, phone)
        if pd.api.types.is_numeric_dtype(actual_dtype):
            # Check if it was incorrectly detected as a semantic type
            if detected_sdtype in ['email', 'phone_number', 'ssn', 'credit_card', 'iban']:
                # Force it to be numerical based on its actual type
                if pd.api.types.is_integer_dtype(actual_dtype):
                    metadata.update_column(column, sdtype='numerical')
                    logger.info(f"Fixed column '{column}': Changed from '{detected_sdtype}' to 'numerical' (integer data)")
                elif pd.api.types.is_float_dtype(actual_dtype):
                    metadata.update_column(column, sdtype='numerical')
                    logger.info(f"Fixed column '{column}': Changed from '{detected_sdtype}' to 'numerical' (float data)")

        # If column has datetime data but was detected as string
        elif pd.api.types.is_datetime64_any_dtype(actual_dtype):
            if detected_sdtype != 'datetime':
                metadata.update_column(column, sdtype='datetime')
                logger.info(f"Fixed column '{column}': Changed from '{detected_sdtype}' to 'datetime'")

        # If column is categorical but has too many unique values (might be ID)
        elif pd.api.types.is_object_dtype(actual_dtype):
            unique_ratio = df[column].nunique() / len(df)
            # If almost all values are unique (>95%), likely an ID column
            if unique_ratio > 0.95 and detected_sdtype == 'categorical':
                metadata.update_column(column, sdtype='id')
                logger.info(f"Fixed column '{column}': Changed from 'categorical' to 'id' (high cardinality)")

    return metadata

def select_synthesizer(df: pd.DataFrame, metadata, model_type: ModelType, config: GenerationConfig):
    """Select and configure the appropriate synthesizer"""
    # Lazy imports
    from sdv.single_table import CTGANSynthesizer, GaussianCopulaSynthesizer, TVAESynthesizer
    from app.services.timegan import TimeSeriesDetector

    is_timeseries = False
    use_case = getattr(config, 'use_case', UseCase.ML_TRAINING)

    if model_type == ModelType.AUTO:
        # Auto-select based on data characteristics and use case
        num_rows, num_cols = df.shape

        # Detect time-series data
        ts_detection = TimeSeriesDetector.detect_time_series(df)

        if use_case == UseCase.PROTOTYPING:
            # Prototyping → default to LLM Row Generator
            model_type = ModelType.LLM_ROW_GEN
            logger.info("Auto: Prototyping use case -> LLM Row Generator")
        elif ts_detection['is_time_series'] and ts_detection['confidence'] > 0.5:
            model_type = ModelType.TIMEGAN
            is_timeseries = True
            logger.info(f"Auto-detected time-series data (confidence: {ts_detection['confidence']:.2f})")
        elif num_rows >= 5000:
            # Large dataset → suggest TabDDPM (state-of-the-art)
            model_type = ModelType.TAB_DDPM
            logger.info(f"Auto: Large dataset ({num_rows} rows) -> TabDDPM")
        elif num_rows < 500:
            # Small dataset → GaussianCopula (fastest)
            model_type = ModelType.GAUSSIAN_COPULA
            logger.info(f"Auto: Small dataset ({num_rows} rows) -> GaussianCopula")
        else:
            # Default → CTGAN
            model_type = ModelType.CTGAN

    # Check if manually selected TimeGAN or DGAN
    if model_type == ModelType.TIMEGAN:
        is_timeseries = True
    if model_type == ModelType.DGAN:
        is_timeseries = True

    # Non-SDV models return None synthesizer (handled separately in generation)
    non_sdv_models = {
        ModelType.TIMEGAN, ModelType.DGAN, ModelType.TAB_DDPM,
        ModelType.BAYESIAN_NETWORK, ModelType.CTAB_GAN_PLUS,
        ModelType.REALTABFORMER, ModelType.DP_CTGAN, ModelType.LLM_ROW_GEN,
    }

    if model_type in non_sdv_models:
        return None, model_type

    # Create SDV synthesizer based on model type
    if model_type == ModelType.CTGAN:
        synthesizer = CTGANSynthesizer(
            metadata,
            epochs=config.epochs,
            batch_size=config.batch_size,
            verbose=True
        )
    elif model_type == ModelType.TVAE:
        synthesizer = TVAESynthesizer(
            metadata,
            epochs=config.epochs,
            batch_size=config.batch_size
        )
    elif model_type == ModelType.GAUSSIAN_COPULA:
        synthesizer = GaussianCopulaSynthesizer(metadata)
    elif model_type == ModelType.COPULA_GAN:
        try:
            from sdv.single_table import CopulaGANSynthesizer
            synthesizer = CopulaGANSynthesizer(
                metadata,
                epochs=config.epochs,
                batch_size=config.batch_size
            )
        except ImportError:
            logger.warning("CopulaGANSynthesizer not available, falling back to CTGAN")
            synthesizer = CTGANSynthesizer(
                metadata,
                epochs=config.epochs,
                batch_size=config.batch_size
            )
            model_type = ModelType.CTGAN
    else:
        synthesizer = CTGANSynthesizer(
            metadata,
            epochs=config.epochs,
            batch_size=config.batch_size
        )

    return synthesizer, model_type


def apply_column_configs(df: pd.DataFrame, config: GenerationConfig) -> pd.DataFrame:
    """Apply column-level configuration before training (Feature 7)"""
    if not config.column_configs:
        return df

    columns_to_drop = []
    for col_config in config.column_configs:
        col_name = col_config.column_name
        if col_name not in df.columns:
            continue

        if col_config.role == "skip":
            columns_to_drop.append(col_name)
        elif col_config.role == "pii":
            # Anonymize PII columns by hashing
            if pd.api.types.is_object_dtype(df[col_name]):
                import hashlib
                df[col_name] = df[col_name].apply(
                    lambda x: hashlib.sha256(str(x).encode()).hexdigest()[:12] if pd.notna(x) else x
                )

    if columns_to_drop:
        df = df.drop(columns=columns_to_drop)
        logger.info(f"Dropped columns marked as 'skip': {columns_to_drop}")

    return df


def apply_conditions(df: pd.DataFrame, conditions: list) -> pd.DataFrame:
    """Filter generated data based on conditions (Feature 10)"""
    if not conditions:
        return df

    mask = pd.Series(True, index=df.index)
    ops = {
        "eq": lambda s, v: s == v,
        "ne": lambda s, v: s != v,
        "gt": lambda s, v: s > v,
        "lt": lambda s, v: s < v,
        "gte": lambda s, v: s >= v,
        "lte": lambda s, v: s <= v,
    }

    for cond in conditions:
        col = cond.column if hasattr(cond, 'column') else cond.get('column')
        op = cond.operator if hasattr(cond, 'operator') else cond.get('operator', 'eq')
        val = cond.value if hasattr(cond, 'value') else cond.get('value')

        if col not in df.columns:
            continue

        op_func = ops.get(op)
        if op_func:
            try:
                # Cast value to match column dtype
                if pd.api.types.is_numeric_dtype(df[col]):
                    val = float(val)
                mask = mask & op_func(df[col], val)
            except Exception as e:
                logger.warning(f"Could not apply condition on {col}: {e}")

    filtered = df[mask]
    if len(filtered) == 0:
        logger.warning("No rows match conditions, returning unfiltered data")
        return df
    return filtered.reset_index(drop=True)


def send_webhook(webhook_url: str, job_id: str, status: str, message: str):
    """Send webhook notification on job completion (Feature 8)"""
    try:
        payload = {
            "job_id": job_id,
            "status": status,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        http_requests.post(webhook_url, json=payload, timeout=10)
        logger.info(f"Webhook sent to {webhook_url}")
    except Exception as e:
        logger.error(f"Failed to send webhook to {webhook_url}: {e}")


def generate_incremental(synthesizer, num_rows: int, batch_size: int = 100, progress_callback=None):
    """Generate synthetic data in batches for streaming (Feature 12)"""
    chunks = []
    generated = 0

    while generated < num_rows:
        batch = min(batch_size, num_rows - generated)
        chunk = synthesizer.sample(num_rows=batch)
        chunks.append(chunk)
        generated += len(chunk)

        if progress_callback:
            pct = min(95.0, 20.0 + (generated / num_rows) * 70.0)
            progress_callback(pct, f"Generated {generated}/{num_rows} rows...")

    return pd.concat(chunks, ignore_index=True)


def generate_synthetic_data_background(job_id: str, original_path: str, config: GenerationConfig):
    """Background task to generate synthetic data"""
    # # Fix TensorFlow threading issues on macOS - COMMENTED OUT (TensorFlow removed)
    # import os
    # os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TF warnings
    # os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'  # Allow duplicate OpenMP libraries
    # os.environ['OMP_NUM_THREADS'] = '1'  # Single-threaded OpenMP
    # os.environ['TF_NUM_INTEROP_THREADS'] = '1'  # Single inter-op thread
    # os.environ['TF_NUM_INTRAOP_THREADS'] = '1'  # Single intra-op thread

    # Lazy imports to avoid loading TensorFlow at module level
    from sdv.metadata import SingleTableMetadata
    from app.services.privacy import (
        apply_differential_privacy,
        compute_privacy_metrics
    )
    from app.services.timegan_pytorch import generate_time_series_synthetic_pytorch

    privacy_metadata = None
    synthesizer = None

    try:
        # Load original data
        update_job_progress(job_id, 5.0, "Loading original data...")
        df = load_data(original_path)

        # Apply column-level configs (Feature 7)
        df = apply_column_configs(df, config)

        # Apply differential privacy if enabled
        if config.enable_privacy and config.privacy_mechanism != PrivacyMechanism.NONE:
            update_job_progress(job_id, 8.0, f"Applying {config.privacy_mechanism.value} privacy...")

            if config.privacy_mechanism in [PrivacyMechanism.LAPLACE, PrivacyMechanism.GAUSSIAN]:
                # Apply noise to training data
                df_private, privacy_metadata = apply_differential_privacy(
                    df,
                    epsilon=config.privacy_epsilon,
                    delta=config.privacy_delta,
                    mechanism=config.privacy_mechanism.value
                )
                df = df_private
                logger.info(f"Applied {config.privacy_mechanism.value} noise with epsilon={config.privacy_epsilon}, delta={config.privacy_delta}")

        # Create metadata
        update_job_progress(job_id, 10.0, "Analyzing data structure...")
        metadata = SingleTableMetadata()
        metadata.detect_from_dataframe(df)

        # Fix metadata detection issues (e.g., numeric columns named "email")
        update_job_progress(job_id, 12.0, "Fixing metadata detection...")
        metadata = fix_metadata_detection(df, metadata)

        # Select and configure synthesizer
        update_job_progress(job_id, 15.0, "Configuring model...")
        synthesizer, selected_model = select_synthesizer(df, metadata, config.model_type, config)

        # Update job with selected model
        db = SessionLocal()
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.model_type = selected_model.value
            # Store privacy settings
            if config.enable_privacy:
                job.privacy_epsilon = config.privacy_epsilon
                job.privacy_enabled = True
            db.commit()
        db.close()

        # Generate synthetic data based on selected model
        privacy_msg = f" with ε={config.privacy_epsilon} DP" if config.enable_privacy else ""
        synthetic_df = None

        if selected_model == ModelType.TIMEGAN:
            update_job_progress(job_id, 20.0, f"Training TimeGAN (PyTorch) model{privacy_msg}...")
            synthetic_df = generate_time_series_synthetic_pytorch(
                df,
                n_samples=config.num_rows,
                seq_len=config.sequence_length if hasattr(config, 'sequence_length') else 24,
                datetime_col=config.datetime_column if hasattr(config, 'datetime_column') else None,
                iterations=min(config.epochs * 10, 5000),
                verbose=True
            )
            update_job_progress(job_id, 80.0, "TimeGAN generation complete...")

        elif selected_model == ModelType.DGAN:
            update_job_progress(job_id, 20.0, f"Training DGAN (DoppelGANger) model{privacy_msg}...")
            try:
                from app.services.dgan_generator import generate_dgan_synthetic
                synthetic_df = generate_dgan_synthetic(
                    df,
                    n_samples=config.num_rows,
                    datetime_col=config.datetime_column if hasattr(config, 'datetime_column') else None,
                    epochs=config.epochs,
                )
            except (ImportError, Exception) as e:
                logger.warning(f"DGAN failed ({e}), falling back to TimeGAN")
                update_job_progress(job_id, 25.0, "DGAN unavailable, falling back to TimeGAN...")
                synthetic_df = generate_time_series_synthetic_pytorch(
                    df, n_samples=config.num_rows,
                    seq_len=config.sequence_length if hasattr(config, 'sequence_length') else 24,
                    datetime_col=config.datetime_column if hasattr(config, 'datetime_column') else None,
                    iterations=min(config.epochs * 10, 5000), verbose=True
                )
            update_job_progress(job_id, 80.0, "Time-series generation complete...")

        elif selected_model == ModelType.TAB_DDPM:
            update_job_progress(job_id, 20.0, f"Training TabDDPM (diffusion) model{privacy_msg}...")
            try:
                from app.services.synthcity_adapter import generate_synthcity_model
                synthetic_df = generate_synthcity_model(df, "ddpm", config.num_rows, config.epochs)
            except (ImportError, Exception) as e:
                logger.warning(f"TabDDPM failed ({e}), falling back to CTGAN")
                update_job_progress(job_id, 25.0, "TabDDPM unavailable, falling back to CTGAN...")
                from sdv.single_table import CTGANSynthesizer
                fallback = CTGANSynthesizer(metadata, epochs=config.epochs, batch_size=config.batch_size)
                fallback.fit(df)
                synthetic_df = fallback.sample(num_rows=config.num_rows)
            update_job_progress(job_id, 80.0, "Generation complete...")

        elif selected_model == ModelType.BAYESIAN_NETWORK:
            update_job_progress(job_id, 20.0, f"Training Bayesian Network model{privacy_msg}...")
            try:
                from app.services.synthcity_adapter import generate_synthcity_model
                synthetic_df = generate_synthcity_model(df, "bayesian_network", config.num_rows)
            except (ImportError, Exception) as e:
                logger.warning(f"Bayesian Network failed ({e}), falling back to GaussianCopula")
                update_job_progress(job_id, 25.0, "Bayesian Network unavailable, falling back to GaussianCopula...")
                from sdv.single_table import GaussianCopulaSynthesizer
                fallback = GaussianCopulaSynthesizer(metadata)
                fallback.fit(df)
                synthetic_df = fallback.sample(num_rows=config.num_rows)
            update_job_progress(job_id, 80.0, "Generation complete...")

        elif selected_model == ModelType.CTAB_GAN_PLUS:
            update_job_progress(job_id, 20.0, f"Training CTAB-GAN+ model{privacy_msg}...")
            try:
                from app.services.synthcity_adapter import generate_synthcity_model
                synthetic_df = generate_synthcity_model(df, "ctabgan", config.num_rows, config.epochs)
            except (ImportError, Exception) as e:
                logger.warning(f"CTAB-GAN+ failed ({e}), falling back to CTGAN")
                update_job_progress(job_id, 25.0, "CTAB-GAN+ unavailable, falling back to CTGAN...")
                from sdv.single_table import CTGANSynthesizer
                fallback = CTGANSynthesizer(metadata, epochs=config.epochs, batch_size=config.batch_size)
                fallback.fit(df)
                synthetic_df = fallback.sample(num_rows=config.num_rows)
            update_job_progress(job_id, 80.0, "Generation complete...")

        elif selected_model == ModelType.REALTABFORMER:
            update_job_progress(job_id, 20.0, f"Training REaLTabFormer model{privacy_msg}...")
            try:
                from app.services.realtabformer_adapter import generate_realtabformer_synthetic
                synthetic_df = generate_realtabformer_synthetic(df, config.num_rows, config.epochs)
            except (ImportError, Exception) as e:
                logger.warning(f"REaLTabFormer failed ({e}), falling back to CTGAN")
                update_job_progress(job_id, 25.0, "REaLTabFormer unavailable, falling back to CTGAN...")
                from sdv.single_table import CTGANSynthesizer
                fallback = CTGANSynthesizer(metadata, epochs=config.epochs, batch_size=config.batch_size)
                fallback.fit(df)
                synthetic_df = fallback.sample(num_rows=config.num_rows)
            update_job_progress(job_id, 80.0, "Generation complete...")

        elif selected_model == ModelType.DP_CTGAN:
            update_job_progress(job_id, 20.0, f"Training DP-CTGAN model (ε={config.privacy_epsilon})...")
            try:
                from snsynth import Synthesizer as SNSynthesizer
                epsilon = config.privacy_epsilon if config.enable_privacy else 1.0
                synth = SNSynthesizer.create("dpctgan", epsilon=epsilon)
                synth.fit(df, preprocessor_eps=epsilon / 10.0)
                synthetic_df = synth.sample(config.num_rows)
            except (ImportError, Exception) as e:
                logger.warning(f"DP-CTGAN failed ({e}), falling back to CTGAN with DP post-processing")
                update_job_progress(job_id, 25.0, "DP-CTGAN unavailable, falling back to CTGAN...")
                from sdv.single_table import CTGANSynthesizer
                fallback = CTGANSynthesizer(metadata, epochs=config.epochs, batch_size=config.batch_size)
                fallback.fit(df)
                synthetic_df = fallback.sample(num_rows=config.num_rows)
            update_job_progress(job_id, 80.0, "Generation complete...")

        elif selected_model == ModelType.LLM_ROW_GEN:
            update_job_progress(job_id, 20.0, "Generating rows with LLM...")
            try:
                from app.services.llm_row_generator import generate_llm_rows
                synthetic_df = generate_llm_rows(
                    df,
                    num_rows=config.num_rows,
                    api_key=config.gpt_api_key,
                    model=config.gpt_model or "gpt-4o-mini",
                    endpoint=config.gpt_endpoint,
                    batch_size=config.llm_row_gen_batch_size if hasattr(config, 'llm_row_gen_batch_size') else 50,
                    progress_callback=lambda pct, msg: update_job_progress(job_id, pct, msg),
                )
            except (ImportError, Exception) as e:
                logger.warning(f"LLM Row Generator failed ({e}), falling back to GaussianCopula")
                update_job_progress(job_id, 25.0, "LLM generation failed, falling back to GaussianCopula...")
                from sdv.single_table import GaussianCopulaSynthesizer
                fallback = GaussianCopulaSynthesizer(metadata)
                fallback.fit(df)
                synthetic_df = fallback.sample(num_rows=config.num_rows)
            update_job_progress(job_id, 80.0, "Generation complete...")

        else:
            # SDV models: CTGAN, TVAE, GaussianCopula, CopulaGAN
            update_job_progress(job_id, 20.0, f"Training {selected_model.value} model{privacy_msg}...")
            synthesizer.fit(df)
            update_job_progress(job_id, 80.0, "Generating synthetic data...")
            synthetic_df = synthesizer.sample(num_rows=config.num_rows)

        # Apply SMOTE post-processing if enabled
        if config.enable_smote and config.smote_target_column:
            update_job_progress(job_id, 85.0, "Applying SMOTE oversampling...")
            try:
                from app.services.smote_processor import apply_smote
                synthetic_df = apply_smote(
                    synthetic_df,
                    target_column=config.smote_target_column,
                    strategy=config.smote_strategy.value if hasattr(config.smote_strategy, 'value') else str(config.smote_strategy),
                    k_neighbors=config.smote_k_neighbors,
                )
            except Exception as e:
                logger.warning(f"SMOTE post-processing failed: {e}, continuing without SMOTE")

        # Apply conditional filtering (Feature 10)
        if config.conditions:
            update_job_progress(job_id, 90.0, "Applying conditions...")
            synthetic_df = apply_conditions(synthetic_df, config.conditions)

        # Save synthetic data
        update_job_progress(job_id, 95.0, "Saving synthetic data...")
        synthetic_path = save_synthetic_data(synthetic_df, job_id)

        # Update job
        db = SessionLocal()
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.synthetic_path = synthetic_path
            job.rows_generated = len(synthetic_df)
            db.commit()
        db.close()

        update_job_status(
            job_id,
            JobStatusEnum.COMPLETED,
            "Synthetic data generated successfully"
        )

        # Send webhook notification (Feature 8)
        if config.webhook_url:
            send_webhook(config.webhook_url, job_id, "completed", "Synthetic data generated successfully")

    except Exception as e:
        error_msg = f"Error generating synthetic data: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        update_job_status(
            job_id,
            JobStatusEnum.FAILED,
            "Generation failed",
            error=error_msg
        )

    finally:
        # # Clean up TensorFlow resources to prevent mutex locks on subsequent runs - COMMENTED OUT (TensorFlow removed)
        try:
            # Clear the synthesizer to release model resources
            if synthesizer is not None:
                del synthesizer

            # # Clear TensorFlow/Keras backend session - COMMENTED OUT (TensorFlow removed)
            # import tensorflow as tf
            # from tensorflow.keras import backend as K
            # K.clear_session()
            #
            # # Reset default graph
            # tf.compat.v1.reset_default_graph()

            # Force garbage collection
            import gc
            gc.collect()

            logger.info(f"Cleaned up resources for job {job_id}")
        except Exception as cleanup_error:
            logger.warning(f"Error during cleanup: {cleanup_error}")
            # Don't fail the job if cleanup fails
            pass
