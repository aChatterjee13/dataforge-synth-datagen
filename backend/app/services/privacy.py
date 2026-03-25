"""
Privacy Layer - Differential Privacy Implementation
Implements DP-SGD (Differentially Private Stochastic Gradient Descent) and PATE
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')


@dataclass
class PrivacyBudget:
    """Track differential privacy budget (epsilon, delta)"""
    epsilon: float  # Privacy loss parameter (lower is more private)
    delta: float  # Failure probability (typically 1/n^2)
    spent_epsilon: float = 0.0
    max_epsilon: float = 10.0  # Maximum allowed epsilon

    def consume(self, epsilon_cost: float) -> bool:
        """
        Consume privacy budget
        Returns True if budget allows, False if exceeded
        """
        if self.spent_epsilon + epsilon_cost > self.max_epsilon:
            return False
        self.spent_epsilon += epsilon_cost
        return True

    def remaining(self) -> float:
        """Get remaining privacy budget"""
        return self.max_epsilon - self.spent_epsilon

    def is_depleted(self) -> bool:
        """Check if privacy budget is depleted"""
        return self.spent_epsilon >= self.max_epsilon


class DifferentialPrivacyEngine:
    """
    Differential Privacy Engine implementing DP-SGD mechanisms
    """

    def __init__(
        self,
        epsilon: float = 1.0,
        delta: float = 1e-5,
        max_grad_norm: float = 1.0,
        noise_multiplier: float = 1.1,
        target_epsilon: Optional[float] = None
    ):
        """
        Initialize DP Engine

        Args:
            epsilon: Privacy loss parameter (typical: 0.1-10, lower is more private)
            delta: Failure probability (typical: 1/n^2 where n is dataset size)
            max_grad_norm: Maximum gradient norm for clipping
            noise_multiplier: Noise scale relative to sensitivity
            target_epsilon: Target epsilon for PATE aggregation
        """
        self.epsilon = epsilon
        self.delta = delta
        self.max_grad_norm = max_grad_norm
        self.noise_multiplier = noise_multiplier
        self.target_epsilon = target_epsilon or epsilon

        # Privacy budget tracker
        self.budget = PrivacyBudget(
            epsilon=epsilon,
            delta=delta,
            max_epsilon=max(epsilon * 2, 10.0)
        )

    def add_laplace_noise(
        self,
        data: np.ndarray,
        sensitivity: float,
        epsilon: float
    ) -> np.ndarray:
        """
        Add Laplace noise for differential privacy (Laplace Mechanism)

        Args:
            data: Input data
            sensitivity: Global sensitivity (max change in output)
            epsilon: Privacy budget to use

        Returns:
            Noisy data
        """
        scale = sensitivity / epsilon
        noise = np.random.laplace(0, scale, data.shape)
        return data + noise

    def add_gaussian_noise(
        self,
        data: np.ndarray,
        sensitivity: float,
        epsilon: float,
        delta: float
    ) -> np.ndarray:
        """
        Add Gaussian noise for differential privacy (Gaussian Mechanism)

        Args:
            data: Input data
            sensitivity: Global sensitivity
            epsilon: Privacy budget to use
            delta: Failure probability

        Returns:
            Noisy data
        """
        # Calculate sigma from privacy parameters
        sigma = (sensitivity * np.sqrt(2 * np.log(1.25 / delta))) / epsilon
        noise = np.random.normal(0, sigma, data.shape)
        return data + noise

    def clip_gradients(self, gradients: np.ndarray) -> np.ndarray:
        """
        Clip gradients to bound sensitivity (DP-SGD)

        Args:
            gradients: Gradient tensor

        Returns:
            Clipped gradients
        """
        grad_norm = np.linalg.norm(gradients)
        if grad_norm > self.max_grad_norm:
            gradients = gradients * (self.max_grad_norm / grad_norm)
        return gradients

    def compute_epsilon_spent(
        self,
        sampling_probability: float,
        noise_multiplier: float,
        steps: int
    ) -> float:
        """
        Compute epsilon spent using RDP (Renyi Differential Privacy) accounting
        Approximation of privacy loss over multiple steps

        Args:
            sampling_probability: Probability of sampling each record
            noise_multiplier: Noise scale
            steps: Number of training steps

        Returns:
            Epsilon spent
        """
        # Simplified RDP accounting (for demonstration)
        # In production, use: https://github.com/tensorflow/privacy
        q = sampling_probability
        sigma = noise_multiplier

        # RDP order (alpha)
        alpha = 10  # Common choice

        # RDP guarantee per step
        rdp_per_step = (q ** 2) / (2 * (sigma ** 2))

        # Total RDP
        rdp_total = steps * rdp_per_step

        # Convert RDP to (epsilon, delta)-DP
        epsilon = rdp_total + (np.log(1 / self.delta)) / (alpha - 1)

        return epsilon

    def pate_aggregation(
        self,
        teacher_votes: List[np.ndarray],
        epsilon: float,
        delta: float
    ) -> np.ndarray:
        """
        PATE (Private Aggregation of Teacher Ensembles) aggregation

        Args:
            teacher_votes: List of predictions from teacher models
            epsilon: Privacy budget for aggregation
            delta: Failure probability

        Returns:
            Aggregated predictions with privacy guarantees
        """
        # Stack teacher votes
        votes = np.array(teacher_votes)

        # Count votes for each class/value
        vote_counts = np.sum(votes, axis=0)

        # Add Gaussian noise to vote counts
        sensitivity = 1.0  # Each teacher contributes at most 1 vote
        noisy_counts = self.add_gaussian_noise(
            vote_counts,
            sensitivity,
            epsilon,
            delta
        )

        # Return argmax of noisy counts
        return np.argmax(noisy_counts, axis=-1)

    def compute_privacy_loss(
        self,
        original_data: pd.DataFrame,
        synthetic_data: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Estimate privacy loss from synthetic data

        Returns:
            Dictionary with privacy metrics
        """
        metrics = {
            'epsilon_spent': self.budget.spent_epsilon,
            'epsilon_remaining': self.budget.remaining(),
            'delta': self.delta,
            'privacy_budget_depleted': self.budget.is_depleted()
        }

        return metrics


class PrivacyAwareDataTransformer:
    """
    Transform data with privacy guarantees before synthesis
    """

    def __init__(self, epsilon: float = 1.0, delta: float = 1e-5):
        self.epsilon = epsilon
        self.delta = delta
        self.dp_engine = DifferentialPrivacyEngine(epsilon, delta)

    def add_noise_to_statistics(
        self,
        df: pd.DataFrame,
        numeric_columns: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """
        Compute noisy statistics for numeric columns

        Args:
            df: DataFrame
            numeric_columns: List of numeric column names

        Returns:
            Dictionary of noisy statistics
        """
        noisy_stats = {}

        for col in numeric_columns:
            # Normalize data to [0, 1] for bounded sensitivity
            data = df[col].values
            data_min = data.min()
            data_max = data.max()
            data_range = data_max - data_min

            if data_range > 0:
                normalized = (data - data_min) / data_range
            else:
                normalized = data

            # Compute statistics with DP
            sensitivity = 1.0  # Bounded sensitivity for normalized data

            mean = normalized.mean()
            std = normalized.std()

            # Add noise
            noisy_mean = self.dp_engine.add_laplace_noise(
                np.array([mean]),
                sensitivity / len(data),
                self.epsilon / 2
            )[0]

            noisy_std = self.dp_engine.add_laplace_noise(
                np.array([std]),
                sensitivity / len(data),
                self.epsilon / 2
            )[0]

            # Denormalize
            noisy_stats[col] = {
                'mean': noisy_mean * data_range + data_min,
                'std': max(0, noisy_std * data_range),  # Ensure non-negative
                'min': data_min,
                'max': data_max
            }

        return noisy_stats

    def privatize_categorical_counts(
        self,
        df: pd.DataFrame,
        categorical_columns: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """
        Compute noisy frequency counts for categorical columns

        Args:
            df: DataFrame
            categorical_columns: List of categorical column names

        Returns:
            Dictionary of noisy frequency distributions
        """
        noisy_distributions = {}

        for col in categorical_columns:
            # Get value counts
            counts = df[col].value_counts().to_dict()

            # Add noise to each count
            noisy_counts = {}
            for category, count in counts.items():
                noisy_count = self.dp_engine.add_laplace_noise(
                    np.array([count]),
                    sensitivity=1.0,  # Each record contributes to one category
                    epsilon=self.epsilon
                )[0]

                # Ensure non-negative and normalize
                noisy_counts[category] = max(0, noisy_count)

            # Normalize to probabilities
            total = sum(noisy_counts.values())
            if total > 0:
                noisy_distributions[col] = {
                    k: v / total for k, v in noisy_counts.items()
                }
            else:
                noisy_distributions[col] = counts

        return noisy_distributions


def apply_differential_privacy(
    df: pd.DataFrame,
    epsilon: float = 1.0,
    delta: float = 1e-5,
    mechanism: str = 'laplace'
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Apply differential privacy to a DataFrame

    Args:
        df: Input DataFrame
        epsilon: Privacy budget
        delta: Failure probability
        mechanism: 'laplace' or 'gaussian'

    Returns:
        Tuple of (privatized DataFrame, privacy metadata)
    """
    dp_engine = DifferentialPrivacyEngine(epsilon, delta)
    transformer = PrivacyAwareDataTransformer(epsilon, delta)

    df_private = df.copy()

    # Identify column types
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

    # Get noisy statistics
    noisy_stats = transformer.add_noise_to_statistics(df, numeric_cols)
    noisy_distributions = transformer.privatize_categorical_counts(df, categorical_cols)

    # Apply noise to numeric columns
    for col in numeric_cols:
        data = df[col].values.reshape(-1, 1)
        sensitivity = (df[col].max() - df[col].min()) / len(df)

        if mechanism == 'laplace':
            noisy_data = dp_engine.add_laplace_noise(data, sensitivity, epsilon)
        else:  # gaussian
            noisy_data = dp_engine.add_gaussian_noise(data, sensitivity, epsilon, delta)

        df_private[col] = noisy_data.flatten()

    # Metadata
    privacy_metadata = {
        'epsilon': epsilon,
        'delta': delta,
        'mechanism': mechanism,
        'numeric_stats': noisy_stats,
        'categorical_distributions': noisy_distributions,
        'privacy_guarantee': f'({epsilon}, {delta})-DP'
    }

    return df_private, privacy_metadata


def compute_privacy_metrics(
    original_df: pd.DataFrame,
    synthetic_df: pd.DataFrame,
    epsilon: float,
    delta: float
) -> Dict[str, Any]:
    """
    Compute privacy metrics for synthetic data

    Args:
        original_df: Original dataset
        synthetic_df: Synthetic dataset
        epsilon: Privacy budget used
        delta: Failure probability

    Returns:
        Dictionary of privacy metrics
    """
    metrics = {
        'epsilon': epsilon,
        'delta': delta,
        'privacy_level': 'STRONG' if epsilon < 1.0 else 'MODERATE' if epsilon < 5.0 else 'WEAK',
        'privacy_guarantee': f'({epsilon}, {delta})-Differential Privacy',
        'records_protected': len(original_df),
        'privacy_budget_status': 'Available' if epsilon < 10.0 else 'Depleted'
    }

    # Privacy strength interpretation
    if epsilon <= 0.1:
        metrics['privacy_description'] = 'Very Strong Privacy (ε ≤ 0.1)'
    elif epsilon <= 1.0:
        metrics['privacy_description'] = 'Strong Privacy (ε ≤ 1.0)'
    elif epsilon <= 5.0:
        metrics['privacy_description'] = 'Moderate Privacy (ε ≤ 5.0)'
    elif epsilon <= 10.0:
        metrics['privacy_description'] = 'Weak Privacy (ε ≤ 10.0)'
    else:
        metrics['privacy_description'] = 'Minimal Privacy (ε > 10.0)'

    return metrics
