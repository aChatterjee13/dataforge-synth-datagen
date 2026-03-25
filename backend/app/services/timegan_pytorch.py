"""
TimeGAN Implementation using PyTorch for Time-Series Synthetic Data Generation
Based on: "Time-series Generative Adversarial Networks" (NeurIPS 2019)
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from typing import Tuple, Optional, Dict, Any
import warnings
warnings.filterwarnings('ignore')

from app.utils.logger import get_logger

logger = get_logger(__name__)


class EmbedderNetwork(nn.Module):
    """Embedder Network: Maps real data to latent space (Optimized with Bidirectional LSTM)"""

    def __init__(self, input_dim: int, hidden_dim: int, num_layers: int = 3, use_bidirectional: bool = True):
        super().__init__()
        self.use_bidirectional = use_bidirectional

        # Use LSTM instead of GRU for better long-term dependencies
        self.rnn = nn.LSTM(
            input_dim,
            hidden_dim,
            num_layers,
            batch_first=True,
            dropout=0.3 if num_layers > 1 else 0,
            bidirectional=use_bidirectional
        )

        # Adjust linear layer dimension if bidirectional
        rnn_output_dim = hidden_dim * 2 if use_bidirectional else hidden_dim
        self.linear = nn.Linear(rnn_output_dim, hidden_dim)
        self.activation = nn.Sigmoid()
        self.layer_norm = nn.LayerNorm(hidden_dim)
        self.batch_norm = nn.BatchNorm1d(input_dim)

    def forward(self, x):
        # Apply batch normalization to input
        x_norm = self.batch_norm(x.transpose(1, 2)).transpose(1, 2)
        h, _ = self.rnn(x_norm)
        h = self.linear(h)
        h = self.layer_norm(h)
        return self.activation(h)


class RecoveryNetwork(nn.Module):
    """Recovery Network: Maps latent space back to data space (Optimized with Bidirectional LSTM)"""

    def __init__(self, hidden_dim: int, output_dim: int, num_layers: int = 3, use_bidirectional: bool = True):
        super().__init__()
        self.use_bidirectional = use_bidirectional

        # Use LSTM instead of GRU
        self.rnn = nn.LSTM(
            hidden_dim,
            hidden_dim,
            num_layers,
            batch_first=True,
            dropout=0.3 if num_layers > 1 else 0,
            bidirectional=use_bidirectional
        )

        # Adjust linear layer dimension if bidirectional
        rnn_output_dim = hidden_dim * 2 if use_bidirectional else hidden_dim
        self.linear = nn.Linear(rnn_output_dim, output_dim)
        self.activation = nn.Sigmoid()
        self.layer_norm = nn.LayerNorm(rnn_output_dim)

    def forward(self, h):
        x, _ = self.rnn(h)
        x = self.layer_norm(x)
        x = self.linear(x)
        return self.activation(x)


class GeneratorNetwork(nn.Module):
    """Generator Network: Generates synthetic latent representations (Optimized with Bidirectional LSTM)"""

    def __init__(self, input_dim: int, hidden_dim: int, num_layers: int = 3, use_bidirectional: bool = True):
        super().__init__()
        self.use_bidirectional = use_bidirectional

        # Use LSTM instead of GRU
        self.rnn = nn.LSTM(
            input_dim,
            hidden_dim,
            num_layers,
            batch_first=True,
            dropout=0.3 if num_layers > 1 else 0,
            bidirectional=use_bidirectional
        )

        # Adjust linear layer dimension if bidirectional
        rnn_output_dim = hidden_dim * 2 if use_bidirectional else hidden_dim
        self.linear = nn.Linear(rnn_output_dim, hidden_dim)
        self.activation = nn.Sigmoid()
        self.layer_norm = nn.LayerNorm(hidden_dim)

    def forward(self, z):
        e, _ = self.rnn(z)
        e = self.linear(e)
        e = self.layer_norm(e)
        return self.activation(e)


class DiscriminatorNetwork(nn.Module):
    """Discriminator Network: Distinguishes real from fake"""

    def __init__(self, hidden_dim: int, num_layers: int = 3):
        super().__init__()
        self.rnn = nn.GRU(hidden_dim, hidden_dim, num_layers, batch_first=True)
        self.linear = nn.Linear(hidden_dim, 1)
        self.activation = nn.Sigmoid()

    def forward(self, h):
        y, _ = self.rnn(h)
        y = self.linear(y)
        return self.activation(y)


class SupervisorNetwork(nn.Module):
    """Supervisor Network: Learns step-wise transitions"""

    def __init__(self, hidden_dim: int, num_layers: int = 2):
        super().__init__()
        self.rnn = nn.GRU(hidden_dim, hidden_dim, num_layers, batch_first=True)
        self.linear = nn.Linear(hidden_dim, hidden_dim)
        self.activation = nn.Sigmoid()

    def forward(self, h):
        s, _ = self.rnn(h)
        s = self.linear(s)
        return self.activation(s)


class TimeGANPyTorch:
    """
    TimeGAN: Time-series Generative Adversarial Networks (PyTorch Implementation)
    """

    def __init__(
        self,
        seq_len: int = 24,
        n_features: int = 1,
        hidden_dim: int = 64,  # Increased from 24 for better capacity
        num_layers: int = 3,
        iterations: int = 10000,
        batch_size: int = 128,
        learning_rate: float = 1e-3,
        device: str = None,
        use_bidirectional: bool = True,  # NEW: Enable bidirectional LSTM
        early_stopping_patience: int = 1000  # NEW: Early stopping patience
    ):
        """
        Initialize TimeGAN (Optimized)

        Args:
            seq_len: Sequence length for time-series
            n_features: Number of features/variables
            hidden_dim: Hidden dimension size (default 64, increased for better capacity)
            num_layers: Number of layers in networks
            iterations: Training iterations
            batch_size: Batch size
            learning_rate: Learning rate
            device: 'cuda', 'cpu', or None (auto-detect)
            use_bidirectional: Use bidirectional LSTM (better temporal modeling)
            early_stopping_patience: Stop training if no improvement for this many iterations
        """
        self.seq_len = seq_len
        self.n_features = n_features
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.iterations = iterations
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.use_bidirectional = use_bidirectional
        self.early_stopping_patience = early_stopping_patience

        # Set device
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)

        logger.info(f"Using device: {self.device}")
        logger.info(f"Bidirectional LSTM: {use_bidirectional}")
        logger.info(f"Hidden dimension: {hidden_dim}")

        # Build networks with bidirectional support
        self.embedder = EmbedderNetwork(n_features, hidden_dim, num_layers, use_bidirectional).to(self.device)
        self.recovery = RecoveryNetwork(hidden_dim, n_features, num_layers, use_bidirectional).to(self.device)
        self.generator = GeneratorNetwork(n_features, hidden_dim, num_layers, use_bidirectional).to(self.device)
        self.discriminator = DiscriminatorNetwork(hidden_dim, num_layers).to(self.device)
        self.supervisor = SupervisorNetwork(hidden_dim, num_layers - 1).to(self.device)

        # Optimizers
        self.embedder_optimizer = optim.Adam(
            list(self.embedder.parameters()) + list(self.recovery.parameters()),
            lr=learning_rate
        )
        self.generator_optimizer = optim.Adam(
            list(self.generator.parameters()) + list(self.supervisor.parameters()),
            lr=learning_rate
        )
        self.discriminator_optimizer = optim.Adam(
            self.discriminator.parameters(),
            lr=learning_rate
        )

        # Learning rate schedulers for adaptive learning
        self.embedder_scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.embedder_optimizer, mode='min', factor=0.5, patience=200
        )
        self.generator_scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.generator_optimizer, mode='min', factor=0.5, patience=200
        )
        self.discriminator_scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.discriminator_optimizer, mode='min', factor=0.5, patience=200
        )

        # Loss functions
        self.mse_loss = nn.MSELoss()
        self.bce_loss = nn.BCELoss()

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

        # Convert to tensor
        data_tensor = torch.FloatTensor(data_normalized).to(self.device)

        # Early stopping variables
        best_loss = float('inf')
        patience_counter = 0

        # Training loop
        for iteration in range(self.iterations):
            # Sample batch
            idx = np.random.randint(0, len(data_normalized), self.batch_size)
            X_batch = data_tensor[idx]

            # Generate random noise
            Z_batch = torch.rand(self.batch_size, self.seq_len, self.n_features).to(self.device)

            # ========== Train Embedder & Recovery ==========
            self.embedder_optimizer.zero_grad()

            H = self.embedder(X_batch)
            X_tilde = self.recovery(H)
            loss_reconstruction = self.mse_loss(X_batch, X_tilde)

            loss_reconstruction.backward()
            torch.nn.utils.clip_grad_norm_(
                list(self.embedder.parameters()) + list(self.recovery.parameters()), 1.0
            )
            self.embedder_optimizer.step()

            # ========== Train Supervisor ==========
            self.generator_optimizer.zero_grad()

            H = self.embedder(X_batch).detach()
            H_supervise = self.supervisor(H)

            # Supervisor loss (predict next step)
            loss_supervisor = self.mse_loss(H[:, 1:, :], H_supervise[:, :-1, :])

            loss_supervisor.backward()
            torch.nn.utils.clip_grad_norm_(
                list(self.generator.parameters()) + list(self.supervisor.parameters()), 1.0
            )
            self.generator_optimizer.step()

            # ========== Train Generator ==========
            self.generator_optimizer.zero_grad()

            E_hat = self.generator(Z_batch)
            H_hat = self.supervisor(E_hat)
            Y_fake = self.discriminator(E_hat)

            # Generator tries to fool discriminator
            loss_generator_unsupervised = self.bce_loss(
                Y_fake,
                torch.ones_like(Y_fake)
            )

            # Moments loss (match statistical moments)
            X_hat = self.recovery(E_hat)
            loss_moments = torch.mean(torch.abs(
                torch.mean(X_batch, dim=0) - torch.mean(X_hat, dim=0)
            )) + torch.mean(torch.abs(
                torch.std(X_batch, dim=0) - torch.std(X_hat, dim=0)
            ))

            # Supervisor loss for generator
            loss_supervisor_gen = self.mse_loss(
                H_hat[:, 1:, :],
                E_hat[:, :-1, :].detach()
            )

            # Improved loss weighting for better quality
            loss_generator = (
                loss_generator_unsupervised +
                100 * torch.sqrt(loss_moments + 1e-8) +
                100 * loss_supervisor_gen  # Increased weight for temporal consistency
            )

            loss_generator.backward()
            torch.nn.utils.clip_grad_norm_(
                list(self.generator.parameters()) + list(self.supervisor.parameters()), 1.0
            )
            self.generator_optimizer.step()

            # ========== Train Discriminator ==========
            self.discriminator_optimizer.zero_grad()

            H = self.embedder(X_batch).detach()
            E_hat = self.generator(Z_batch).detach()

            Y_real = self.discriminator(H)
            Y_fake = self.discriminator(E_hat)

            loss_discriminator = (
                self.bce_loss(Y_real, torch.ones_like(Y_real)) +
                self.bce_loss(Y_fake, torch.zeros_like(Y_fake))
            )

            loss_discriminator.backward()
            torch.nn.utils.clip_grad_norm_(self.discriminator.parameters(), 1.0)
            self.discriminator_optimizer.step()

            # Calculate combined loss for early stopping
            combined_loss = loss_reconstruction.item() + loss_generator.item() + loss_discriminator.item()

            # Update learning rate schedulers
            self.embedder_scheduler.step(loss_reconstruction)
            self.generator_scheduler.step(loss_generator)
            self.discriminator_scheduler.step(loss_discriminator)

            # Early stopping check
            if combined_loss < best_loss:
                best_loss = combined_loss
                patience_counter = 0
            else:
                patience_counter += 1

            if patience_counter >= self.early_stopping_patience:
                if verbose:
                    logger.info(f"Early stopping at iteration {iteration + 1}")
                    logger.info(f"Best loss: {best_loss:.4f}")
                break

            # Print progress
            if verbose and (iteration + 1) % 500 == 0:
                logger.info(f"Iteration {iteration + 1}/{self.iterations} | "
                      f"Reconstruction: {loss_reconstruction.item():.4f} | "
                      f"Generator: {loss_generator.item():.4f} | "
                      f"Discriminator: {loss_discriminator.item():.4f} | "
                      f"Supervisor: {loss_supervisor.item():.4f} | "
                      f"Combined: {combined_loss:.4f} | "
                      f"Best: {best_loss:.4f}")

    def generate(self, n_samples: int) -> np.ndarray:
        """
        Generate synthetic time-series data

        Args:
            n_samples: Number of sequences to generate

        Returns:
            Synthetic time-series data of shape (n_samples, seq_len, n_features)
        """
        self.generator.eval()
        self.recovery.eval()

        with torch.no_grad():
            # Generate random noise
            Z = torch.rand(n_samples, self.seq_len, self.n_features).to(self.device)

            # Generate latent representation
            E_hat = self.generator(Z)

            # Recover to data space
            X_hat = self.recovery(E_hat)

            # Convert to numpy and denormalize
            X_hat_np = X_hat.cpu().numpy()
            X_hat_denorm = X_hat_np * (self.data_max - self.data_min + 1e-7) + self.data_min

        self.generator.train()
        self.recovery.train()

        return X_hat_denorm

    def save(self, filepath: str):
        """Save model weights"""
        torch.save({
            'embedder': self.embedder.state_dict(),
            'recovery': self.recovery.state_dict(),
            'generator': self.generator.state_dict(),
            'discriminator': self.discriminator.state_dict(),
            'supervisor': self.supervisor.state_dict(),
            'data_min': self.data_min,
            'data_max': self.data_max,
            'config': {
                'seq_len': self.seq_len,
                'n_features': self.n_features,
                'hidden_dim': self.hidden_dim,
                'num_layers': self.num_layers
            }
        }, filepath)
        logger.info(f"Model saved to {filepath}")

    def load(self, filepath: str):
        """Load model weights"""
        checkpoint = torch.load(filepath, map_location=self.device)

        self.embedder.load_state_dict(checkpoint['embedder'])
        self.recovery.load_state_dict(checkpoint['recovery'])
        self.generator.load_state_dict(checkpoint['generator'])
        self.discriminator.load_state_dict(checkpoint['discriminator'])
        self.supervisor.load_state_dict(checkpoint['supervisor'])

        self.data_min = checkpoint['data_min']
        self.data_max = checkpoint['data_max']

        logger.info(f"Model loaded from {filepath}")


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


def generate_time_series_synthetic_pytorch(
    original_df: pd.DataFrame,
    n_samples: int = 1000,
    seq_len: int = 24,
    datetime_col: Optional[str] = None,
    iterations: int = 10000,  # Increased for better quality
    hidden_dim: int = None,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Generate synthetic time-series data using TimeGAN (PyTorch)

    Args:
        original_df: Original time-series dataframe
        n_samples: Number of samples to generate
        seq_len: Sequence length
        datetime_col: Name of datetime column
        iterations: Training iterations
        hidden_dim: Hidden dimension (auto if None)
        verbose: Print progress

    Returns:
        Synthetic time-series dataframe
    """
    # Prepare data
    sequences, metadata = prepare_time_series_data(original_df, seq_len, datetime_col)

    if len(sequences) == 0:
        raise ValueError(f"Not enough data to create sequences of length {seq_len}")

    # Auto-set hidden dim if not provided (increased for better quality)
    if hidden_dim is None:
        hidden_dim = min(64, max(32, metadata['n_features'] * 4))

    # Initialize TimeGAN (Optimized)
    timegan = TimeGANPyTorch(
        seq_len=seq_len,
        n_features=metadata['n_features'],
        hidden_dim=hidden_dim,
        num_layers=3,
        iterations=iterations,
        batch_size=min(128, max(16, len(sequences) // 4)),
        use_bidirectional=True,  # Enable bidirectional LSTM
        early_stopping_patience=1000  # Early stopping for efficiency
    )

    # Train
    if verbose:
        logger.info(f"Training TimeGAN (PyTorch) on {len(sequences)} sequences...")
        logger.info(f"Features: {metadata['feature_names']}")

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
        if verbose:
            logger.info(f"Reconstructing datetime column: {datetime_col}")
            logger.debug(f"Original dtype: {original_df[datetime_col].dtype}")

        # Try to parse as datetime if not already
        try:
            if not pd.api.types.is_datetime64_any_dtype(original_df[datetime_col]):
                datetime_series = pd.to_datetime(original_df[datetime_col])
                if verbose:
                    logger.debug("Converted to datetime")
            else:
                datetime_series = original_df[datetime_col]

            start_date = datetime_series.min()
            freq = pd.infer_freq(datetime_series.iloc[:min(100, len(datetime_series))])

            if verbose:
                logger.debug(f"Start date: {start_date}")
                logger.debug(f"Inferred frequency: {freq}")

            if freq:
                date_range = pd.date_range(start=start_date, periods=len(synthetic_df), freq=freq)
            else:
                # Default to daily frequency
                if verbose:
                    logger.debug("Could not infer frequency, using daily")
                date_range = pd.date_range(start=start_date, periods=len(synthetic_df), freq='D')

            synthetic_df[datetime_col] = date_range

            if verbose:
                logger.info(f"Added datetime column with {len(date_range)} values")
                logger.debug(f"Range: {date_range[0]} to {date_range[-1]}")

        except Exception as e:
            if verbose:
                logger.error(f"Failed to add datetime column: {e}")
                logger.warning("Continuing without datetime column")
    elif datetime_col:
        if verbose:
            logger.warning(f"Datetime column '{datetime_col}' specified but not found in original data")
            logger.debug(f"Available columns: {list(original_df.columns)}")

    if verbose:
        logger.info(f"Generated {len(synthetic_df)} synthetic time-series samples")
        logger.debug(f"Final columns: {list(synthetic_df.columns)}")

    return synthetic_df
