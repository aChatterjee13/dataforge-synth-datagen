"""
TimeGAN Implementation for Time-Series Synthetic Data Generation
Implements TimeGAN and RGAN for temporal dependencies preservation
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, List, Dict, Any
import warnings
warnings.filterwarnings('ignore')

from app.utils.logger import get_logger

logger = get_logger(__name__)

# TensorFlow imports are lazy-loaded inside functions to avoid mutex deadlock on macOS


class TimeSeriesDetector:
    """
    Detect if a dataset contains time-series characteristics
    """

    @staticmethod
    def detect_time_series(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect time-series patterns in dataframe

        Returns:
            Dictionary with detection results
        """
        results = {
            'is_time_series': False,
            'datetime_columns': [],
            'sequence_columns': [],
            'temporal_features': [],
            'has_regular_intervals': False,
            'confidence': 0.0
        }

        # Check for datetime columns
        datetime_cols = []
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                datetime_cols.append(col)
            elif df[col].dtype == 'object':
                try:
                    pd.to_datetime(df[col])
                    datetime_cols.append(col)
                except:
                    pass

        results['datetime_columns'] = datetime_cols

        # Check for sequence/index patterns
        if len(datetime_cols) > 0:
            results['is_time_series'] = True
            results['confidence'] += 0.5

        # Check for temporal keywords in column names
        temporal_keywords = ['time', 'date', 'year', 'month', 'day', 'hour',
                            'minute', 'second', 'timestamp', 'period', 'sequence']

        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in temporal_keywords):
                results['temporal_features'].append(col)
                results['confidence'] += 0.1

        # Check for sequential index
        if df.index.is_monotonic_increasing:
            results['has_regular_intervals'] = True
            results['confidence'] += 0.2

        results['confidence'] = min(1.0, results['confidence'])

        if results['confidence'] > 0.3:
            results['is_time_series'] = True

        return results


class TimeGAN:
    """
    TimeGAN: Time-series Generative Adversarial Networks
    Based on: "Time-series Generative Adversarial Networks" (NeurIPS 2019)
    """

    def __init__(
        self,
        seq_len: int = 24,
        n_features: int = 1,
        hidden_dim: int = 24,
        num_layers: int = 3,
        iterations: int = 10000,
        batch_size: int = 128,
        learning_rate: float = 1e-3
    ):
        """
        Initialize TimeGAN

        Args:
            seq_len: Sequence length for time-series
            n_features: Number of features/variables
            hidden_dim: Hidden dimension size
            num_layers: Number of layers in networks
            iterations: Training iterations
            batch_size: Batch size
            learning_rate: Learning rate
        """
        # Lazy import TensorFlow to avoid mutex deadlock on macOS
        import tensorflow as tf
        from tensorflow import keras
        from tensorflow.keras import layers

        # Store as instance variables for use in other methods
        self.tf = tf
        self.keras = keras
        self.layers = layers

        self.seq_len = seq_len
        self.n_features = n_features
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.iterations = iterations
        self.batch_size = batch_size
        self.learning_rate = learning_rate

        # Build networks
        self.embedder = self._build_embedder()
        self.recovery = self._build_recovery()
        self.generator = self._build_generator()
        self.discriminator = self._build_discriminator()
        self.supervisor = self._build_supervisor()

    def _build_embedder(self) -> "keras.Model":
        """Build embedder network (maps real data to latent space)"""
        inputs = self.layers.Input(shape=(self.seq_len, self.n_features))

        # GRU layers
        x = inputs
        for i in range(self.num_layers):
            x = self.layers.GRU(
                self.hidden_dim,
                return_sequences=True,
                name=f'embedder_gru_{i}'
            )(x)

        outputs = self.layers.Dense(self.hidden_dim, activation='sigmoid', name='embedder_output')(x)

        return self.keras.Model(inputs, outputs, name='Embedder')

    def _build_recovery(self) -> "keras.Model":
        """Build recovery network (maps latent space back to data space)"""
        inputs = self.layers.Input(shape=(self.seq_len, self.hidden_dim))

        # GRU layers
        x = inputs
        for i in range(self.num_layers):
            x = self.layers.GRU(
                self.hidden_dim,
                return_sequences=True,
                name=f'recovery_gru_{i}'
            )(x)

        outputs = self.layers.Dense(self.n_features, activation='sigmoid', name='recovery_output')(x)

        return self.keras.Model(inputs, outputs, name='Recovery')

    def _build_generator(self) -> "keras.Model":
        """Build generator network (generates synthetic latent representations)"""
        inputs = self.layers.Input(shape=(self.seq_len, self.n_features))

        # GRU layers
        x = inputs
        for i in range(self.num_layers):
            x = self.layers.GRU(
                self.hidden_dim,
                return_sequences=True,
                name=f'generator_gru_{i}'
            )(x)

        outputs = self.layers.Dense(self.hidden_dim, activation='sigmoid', name='generator_output')(x)

        return self.keras.Model(inputs, outputs, name='Generator')

    def _build_discriminator(self) -> "keras.Model":
        """Build discriminator network (distinguishes real from fake)"""
        inputs = self.layers.Input(shape=(self.seq_len, self.hidden_dim))

        # GRU layers
        x = inputs
        for i in range(self.num_layers):
            x = self.layers.GRU(
                self.hidden_dim,
                return_sequences=True,
                name=f'discriminator_gru_{i}'
            )(x)

        outputs = self.layers.Dense(1, activation='sigmoid', name='discriminator_output')(x)

        return self.keras.Model(inputs, outputs, name='Discriminator')

    def _build_supervisor(self) -> "keras.Model":
        """Build supervisor network (learns step-wise transitions)"""
        inputs = self.layers.Input(shape=(self.seq_len, self.hidden_dim))

        # GRU layers
        x = inputs
        for i in range(self.num_layers - 1):
            x = self.layers.GRU(
                self.hidden_dim,
                return_sequences=True,
                name=f'supervisor_gru_{i}'
            )(x)

        outputs = self.layers.Dense(self.hidden_dim, activation='sigmoid', name='supervisor_output')(x)

        return self.keras.Model(inputs, outputs, name='Supervisor')

    def fit(self, data: np.ndarray, verbose: bool = True):
        """
        Train TimeGAN on time-series data

        Args:
            data: Time-series data of shape (n_samples, seq_len, n_features)
            verbose: Print training progress
        """
        # Normalize data to [0, 1]
        self.data_min = np.min(data, axis=(0, 1))
        self.data_max = np.max(data, axis=(0, 1))
        data_normalized = (data - self.data_min) / (self.data_max - self.data_min + 1e-7)

        # Optimizers
        opt = self.keras.optimizers.Adam(self.learning_rate)

        # Training loop
        for iteration in range(self.iterations):
            # Sample batch
            idx = np.random.randint(0, len(data_normalized), self.batch_size)
            X_batch = data_normalized[idx]

            # Generate random noise
            Z_batch = np.random.uniform(0, 1, size=(self.batch_size, self.seq_len, self.n_features))

            # Train embedder and recovery
            with self.tf.GradientTape() as tape:
                H = self.embedder(X_batch, training=True)
                X_tilde = self.recovery(H, training=True)
                loss_reconstruction = self.tf.reduce_mean(self.tf.abs(X_batch - X_tilde))

            gradients = tape.gradient(
                loss_reconstruction,
                self.embedder.trainable_variables + self.recovery.trainable_variables
            )
            opt.apply_gradients(zip(
                gradients,
                self.embedder.trainable_variables + self.recovery.trainable_variables
            ))

            # Train generator and supervisor
            with self.tf.GradientTape() as tape:
                E_hat = self.generator(Z_batch, training=True)
                H_hat_supervise = self.supervisor(E_hat, training=True)
                X_hat = self.recovery(E_hat, training=True)

                # Generator loss
                Y_fake = self.discriminator(E_hat, training=False)
                loss_generator = -self.tf.reduce_mean(self.tf.math.log(Y_fake + 1e-8))

                # Supervisor loss
                H = self.embedder(X_batch, training=False)
                H_supervise = self.supervisor(H, training=False)
                loss_supervisor = self.tf.reduce_mean(self.tf.abs(H[:, 1:, :] - H_supervise[:, :-1, :]))

                total_loss_g = loss_generator + loss_supervisor

            gradients = tape.gradient(
                total_loss_g,
                self.generator.trainable_variables + self.supervisor.trainable_variables
            )
            opt.apply_gradients(zip(
                gradients,
                self.generator.trainable_variables + self.supervisor.trainable_variables
            ))

            # Train discriminator
            with self.tf.GradientTape() as tape:
                H = self.embedder(X_batch, training=False)
                E_hat = self.generator(Z_batch, training=False)

                Y_real = self.discriminator(H, training=True)
                Y_fake = self.discriminator(E_hat, training=True)

                loss_discriminator = -self.tf.reduce_mean(
                    self.tf.math.log(Y_real + 1e-8) + self.tf.math.log(1. - Y_fake + 1e-8)
                )

            gradients = tape.gradient(loss_discriminator, self.discriminator.trainable_variables)
            opt.apply_gradients(zip(gradients, self.discriminator.trainable_variables))

            # Print progress
            if verbose and (iteration + 1) % 500 == 0:
                logger.info(f"Iteration {iteration + 1}/{self.iterations}, "
                      f"Reconstruction Loss: {loss_reconstruction:.4f}, "
                      f"Generator Loss: {loss_generator:.4f}, "
                      f"Discriminator Loss: {loss_discriminator:.4f}")

    def generate(self, n_samples: int) -> np.ndarray:
        """
        Generate synthetic time-series data

        Args:
            n_samples: Number of sequences to generate

        Returns:
            Synthetic time-series data of shape (n_samples, seq_len, n_features)
        """
        # Generate random noise
        Z = np.random.uniform(0, 1, size=(n_samples, self.seq_len, self.n_features))

        # Generate latent representation
        E_hat = self.generator(Z, training=False)

        # Recover to data space
        X_hat = self.recovery(E_hat, training=False)

        # Denormalize
        X_hat_denorm = X_hat.numpy() * (self.data_max - self.data_min + 1e-7) + self.data_min

        return X_hat_denorm


def prepare_time_series_data(
    df: pd.DataFrame,
    seq_len: int = 24,
    datetime_col: Optional[str] = None
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Prepare time-series data for TimeGAN

    Args:
        df: Input dataframe
        seq_len: Sequence length
        datetime_col: Name of datetime column

    Returns:
        Tuple of (sequences array, metadata)
    """
    # Sort by datetime if provided
    if datetime_col and datetime_col in df.columns:
        df = df.sort_values(datetime_col).reset_index(drop=True)

    # Select numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    # Remove datetime column from numeric cols if it's there
    if datetime_col in numeric_cols:
        numeric_cols.remove(datetime_col)

    data = df[numeric_cols].values

    # Create sequences
    sequences = []
    for i in range(len(data) - seq_len + 1):
        sequences.append(data[i:i + seq_len])

    sequences = np.array(sequences)

    metadata = {
        'seq_len': seq_len,
        'n_features': len(numeric_cols),
        'feature_names': numeric_cols,
        'n_sequences': len(sequences),
        'datetime_col': datetime_col
    }

    return sequences, metadata


def generate_time_series_synthetic(
    original_df: pd.DataFrame,
    n_samples: int = 1000,
    seq_len: int = 24,
    datetime_col: Optional[str] = None,
    iterations: int = 5000,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Generate synthetic time-series data using TimeGAN

    Args:
        original_df: Original time-series dataframe
        n_samples: Number of samples to generate
        seq_len: Sequence length
        datetime_col: Name of datetime column
        iterations: Training iterations
        verbose: Print progress

    Returns:
        Synthetic time-series dataframe
    """
    # Prepare data
    sequences, metadata = prepare_time_series_data(original_df, seq_len, datetime_col)

    # Initialize TimeGAN
    timegan = TimeGAN(
        seq_len=seq_len,
        n_features=metadata['n_features'],
        hidden_dim=min(24, metadata['n_features'] * 2),
        iterations=iterations,
        batch_size=min(128, len(sequences) // 4)
    )

    # Train
    if verbose:
        logger.info(f"Training TimeGAN on {len(sequences)} sequences...")
    timegan.fit(sequences, verbose=verbose)

    # Generate synthetic sequences
    if verbose:
        logger.info(f"Generating {n_samples} synthetic samples...")

    n_sequences = max(1, n_samples // seq_len)
    synthetic_sequences = timegan.generate(n_sequences)

    # Flatten sequences to dataframe
    synthetic_data = synthetic_sequences.reshape(-1, metadata['n_features'])

    # Create dataframe
    synthetic_df = pd.DataFrame(synthetic_data, columns=metadata['feature_names'])

    # Trim to requested number of samples
    synthetic_df = synthetic_df.head(n_samples)

    # Add datetime column if original had one
    if datetime_col and datetime_col in original_df.columns:
        # Generate datetime sequence
        if pd.api.types.is_datetime64_any_dtype(original_df[datetime_col]):
            start_date = original_df[datetime_col].min()
            freq = pd.infer_freq(original_df[datetime_col].iloc[:100])
            if freq:
                date_range = pd.date_range(start=start_date, periods=len(synthetic_df), freq=freq)
            else:
                date_range = pd.date_range(start=start_date, periods=len(synthetic_df), freq='D')
            synthetic_df[datetime_col] = date_range

    return synthetic_df
