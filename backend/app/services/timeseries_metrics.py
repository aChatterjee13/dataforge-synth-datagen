"""
Time-Series Specific Metrics for ML Efficacy and Quality Evaluation
Uses ARIMA and LSTM models with RMSE/MAE metrics
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from typing import Dict, Any, Optional, List, Tuple
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import MinMaxScaler
import warnings
warnings.filterwarnings('ignore')

from app.utils.logger import get_logger
logger = get_logger(__name__)


class AttentionLayer(nn.Module):
    """Self-attention mechanism for LSTM output"""

    def __init__(self, hidden_dim: int):
        super().__init__()
        self.attention = nn.Linear(hidden_dim, 1)

    def forward(self, lstm_output):
        # lstm_output shape: (batch, seq_len, hidden_dim)
        attention_weights = torch.softmax(self.attention(lstm_output), dim=1)
        context = torch.sum(attention_weights * lstm_output, dim=1)
        return context, attention_weights


class LSTMPredictor(nn.Module):
    """Optimized LSTM for time-series prediction with attention and batch normalization"""

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 128,  # Increased from 50
        num_layers: int = 3,  # Increased from 2
        dropout: float = 0.3,
        use_attention: bool = True,
        bidirectional: bool = True
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.use_attention = use_attention
        self.bidirectional = bidirectional

        # Batch normalization for input
        self.input_bn = nn.BatchNorm1d(input_dim)

        # Bidirectional LSTM for better temporal context
        self.lstm = nn.LSTM(
            input_dim,
            hidden_dim,
            num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=bidirectional
        )

        # Calculate LSTM output dimension
        lstm_output_dim = hidden_dim * 2 if bidirectional else hidden_dim

        # Attention mechanism
        if use_attention:
            self.attention = AttentionLayer(lstm_output_dim)
            fc_input_dim = lstm_output_dim
        else:
            fc_input_dim = lstm_output_dim

        # Fully connected layers with residual connection
        self.fc1 = nn.Linear(fc_input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim // 2)
        self.fc3 = nn.Linear(hidden_dim // 2, 1)

        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        self.layer_norm1 = nn.LayerNorm(hidden_dim)
        self.layer_norm2 = nn.LayerNorm(hidden_dim // 2)

    def forward(self, x):
        # x shape: (batch, seq_len, input_dim)
        batch_size, seq_len, input_dim = x.shape

        # Apply batch normalization to input
        x_norm = self.input_bn(x.transpose(1, 2)).transpose(1, 2)

        # LSTM forward pass
        lstm_out, _ = self.lstm(x_norm)

        # Apply attention or take last time step
        if self.use_attention:
            context, _ = self.attention(lstm_out)
        else:
            context = lstm_out[:, -1, :]

        # Fully connected layers with normalization
        out = self.fc1(context)
        out = self.layer_norm1(out)
        out = self.relu(out)
        out = self.dropout(out)

        out = self.fc2(out)
        out = self.layer_norm2(out)
        out = self.relu(out)
        out = self.dropout(out)

        out = self.fc3(out)
        return out


def prepare_sequences_for_prediction(data: np.ndarray, seq_len: int = 10, target_idx: int = 0):
    """
    Prepare sequences for time-series prediction

    Args:
        data: Time-series data (n_samples, n_features)
        seq_len: Sequence length for input
        target_idx: Index of target variable to predict

    Returns:
        X, y arrays for training
    """
    X, y = [], []

    for i in range(len(data) - seq_len):
        X.append(data[i:i+seq_len])
        y.append(data[i+seq_len, target_idx])

    return np.array(X), np.array(y)


def train_lstm_predictor(
    X_train: np.ndarray,
    y_train: np.ndarray,
    epochs: int = 100,  # Increased from 50
    batch_size: int = 64,  # Increased from 32
    learning_rate: float = 0.001,
    device: str = 'cpu',
    use_attention: bool = True,
    early_stopping_patience: int = 15,
    verbose: bool = False
) -> LSTMPredictor:
    """Train optimized LSTM predictor with early stopping and LR scheduling"""

    input_dim = X_train.shape[2]
    model = LSTMPredictor(
        input_dim,
        hidden_dim=128,
        num_layers=3,
        dropout=0.3,
        use_attention=use_attention,
        bidirectional=True
    ).to(device)

    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=1e-5)

    # Learning rate scheduler
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=5
    )

    # Convert to tensors
    X_tensor = torch.FloatTensor(X_train).to(device)
    y_tensor = torch.FloatTensor(y_train).reshape(-1, 1).to(device)

    # Early stopping variables
    best_loss = float('inf')
    patience_counter = 0

    # Training loop
    model.train()
    for epoch in range(epochs):
        # Shuffle data
        indices = np.random.permutation(len(X_train))

        epoch_loss = 0
        num_batches = 0

        for i in range(0, len(indices), batch_size):
            batch_idx = indices[i:min(i+batch_size, len(indices))]

            X_batch = X_tensor[batch_idx]
            y_batch = y_tensor[batch_idx]

            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()

            # Gradient clipping to prevent exploding gradients
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

            optimizer.step()

            epoch_loss += loss.item()
            num_batches += 1

        # Calculate average loss
        avg_loss = epoch_loss / num_batches

        # Update learning rate
        scheduler.step(avg_loss)

        # Early stopping check
        if avg_loss < best_loss:
            best_loss = avg_loss
            patience_counter = 0
        else:
            patience_counter += 1

        if patience_counter >= early_stopping_patience:
            if verbose:
                logger.info(f"Early stopping at epoch {epoch + 1}")
            break

        if verbose and (epoch + 1) % 10 == 0:
            logger.debug(f"Epoch {epoch + 1}/{epochs} | Loss: {avg_loss:.6f}")

    return model


def evaluate_lstm_prediction(
    model: LSTMPredictor,
    X_test: np.ndarray,
    y_test: np.ndarray,
    device: str = 'cpu'
) -> Dict[str, float]:
    """Evaluate LSTM predictions with comprehensive metrics"""

    model.eval()
    with torch.no_grad():
        X_tensor = torch.FloatTensor(X_test).to(device)
        y_pred = model(X_tensor).cpu().numpy().flatten()

    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    # Calculate MAPE (Mean Absolute Percentage Error)
    mape = np.mean(np.abs((y_test - y_pred) / (y_test + 1e-8))) * 100

    return {
        'rmse': float(rmse),
        'mae': float(mae),
        'r2': float(r2),
        'mape': float(mape),
        'predictions': y_pred
    }


def evaluate_arima_prediction(
    train_data: np.ndarray,
    test_data: np.ndarray,
    order: Tuple[int, int, int] = None,
    use_auto: bool = True,
    seasonal: bool = False,
    m: int = 12
) -> Dict[str, float]:
    """
    Evaluate ARIMA model for time-series prediction with Auto ARIMA support

    Args:
        train_data: Training time-series
        test_data: Test time-series
        order: ARIMA (p, d, q) order (if use_auto=False)
        use_auto: Use Auto ARIMA for automatic parameter selection
        seasonal: Enable seasonal ARIMA
        m: Seasonal period (e.g., 12 for monthly data)

    Returns:
        Dictionary with RMSE, MAE, R2, and MAPE
    """
    try:
        if use_auto:
            try:
                from pmdarima import auto_arima

                # Auto ARIMA for optimal parameter selection
                model = auto_arima(
                    train_data,
                    start_p=0, start_q=0,
                    max_p=5, max_q=5,
                    seasonal=seasonal,
                    m=m if seasonal else 1,
                    stepwise=True,
                    suppress_warnings=True,
                    error_action='ignore',
                    trace=False,
                    n_fits=50
                )

                # Forecast
                forecast = model.predict(n_periods=len(test_data))

            except ImportError:
                # Fallback to standard ARIMA if pmdarima not available
                logger.warning("pmdarima not available, using standard ARIMA with default order (1,1,1)")
                from statsmodels.tsa.arima.model import ARIMA
                order = order or (1, 1, 1)
                model = ARIMA(train_data, order=order)
                fitted_model = model.fit()
                forecast = fitted_model.forecast(steps=len(test_data))
        else:
            from statsmodels.tsa.arima.model import ARIMA
            order = order or (1, 1, 1)
            model = ARIMA(train_data, order=order)
            fitted_model = model.fit()
            forecast = fitted_model.forecast(steps=len(test_data))

        # Calculate comprehensive metrics
        rmse = np.sqrt(mean_squared_error(test_data, forecast))
        mae = mean_absolute_error(test_data, forecast)
        r2 = r2_score(test_data, forecast)
        mape = np.mean(np.abs((test_data - forecast) / (test_data + 1e-8))) * 100

        return {
            'rmse': float(rmse),
            'mae': float(mae),
            'r2': float(r2),
            'mape': float(mape),
            'predictions': forecast
        }

    except Exception as e:
        logger.error(f"ARIMA evaluation failed: {e}")
        return {
            'rmse': float('inf'),
            'mae': float('inf'),
            'r2': float('-inf'),
            'mape': float('inf'),
            'predictions': None
        }


class TimeSeriesMLEfficacy:
    """Evaluate time-series synthetic data quality using ARIMA and LSTM"""

    def __init__(
        self,
        original_df: pd.DataFrame,
        synthetic_df: pd.DataFrame,
        datetime_col: Optional[str] = None,
        target_columns: Optional[List[str]] = None
    ):
        self.original_df = original_df
        self.synthetic_df = synthetic_df
        self.datetime_col = datetime_col

        # Select numeric columns
        self.numeric_cols = original_df.select_dtypes(include=[np.number]).columns.tolist()

        # Remove datetime if it's in numeric cols
        if datetime_col and datetime_col in self.numeric_cols:
            self.numeric_cols.remove(datetime_col)

        # Use specified targets or auto-select
        if target_columns:
            self.target_columns = [col for col in target_columns if col in self.numeric_cols]
        else:
            # Auto-select first 2 numeric columns
            self.target_columns = self.numeric_cols[:min(2, len(self.numeric_cols))]

    def evaluate_all(self, seq_len: int = 10) -> Dict[str, Any]:
        """
        Evaluate time-series quality using multiple methods

        Args:
            seq_len: Sequence length for LSTM evaluation

        Returns:
            Dictionary with evaluation results
        """
        results = {
            'lstm_metrics': [],
            'arima_metrics': [],
            'overall_rmse_ratio': 0.0,
            'overall_mae_ratio': 0.0,
            'interpretation': 'POOR'
        }

        if len(self.target_columns) == 0 or len(self.numeric_cols) == 0:
            return results

        # Evaluate each target column
        for target_col in self.target_columns:
            # LSTM evaluation
            lstm_result = self._evaluate_lstm_for_column(target_col, seq_len)
            if lstm_result:
                results['lstm_metrics'].append(lstm_result)

            # ARIMA evaluation
            arima_result = self._evaluate_arima_for_column(target_col)
            if arima_result:
                results['arima_metrics'].append(arima_result)

        # Compute overall metrics
        if results['lstm_metrics']:
            rmse_ratios = [m['efficacy_rmse'] for m in results['lstm_metrics'] if m.get('efficacy_rmse')]
            mae_ratios = [m['efficacy_mae'] for m in results['lstm_metrics'] if m.get('efficacy_mae')]

            if rmse_ratios:
                results['overall_rmse_ratio'] = float(np.mean(rmse_ratios))
            if mae_ratios:
                results['overall_mae_ratio'] = float(np.mean(mae_ratios))

        # Interpretation based on ratios (closer to 1.0 is better)
        avg_ratio = (results['overall_rmse_ratio'] + results['overall_mae_ratio']) / 2

        if avg_ratio >= 0.85:
            results['interpretation'] = 'EXCELLENT'
        elif avg_ratio >= 0.70:
            results['interpretation'] = 'GOOD'
        elif avg_ratio >= 0.50:
            results['interpretation'] = 'MODERATE'
        else:
            results['interpretation'] = 'POOR'

        return results

    def _evaluate_lstm_for_column(self, target_col: str, seq_len: int = 10) -> Optional[Dict[str, Any]]:
        """Evaluate LSTM prediction for a specific column"""
        try:
            # Get data
            original_data = self.original_df[self.numeric_cols].values
            synthetic_data = self.synthetic_df[self.numeric_cols].values

            target_idx = self.numeric_cols.index(target_col)

            # Check minimum data requirement
            if len(original_data) < seq_len + 20:
                return None

            # Normalize
            scaler = MinMaxScaler()
            original_scaled = scaler.fit_transform(original_data)
            synthetic_scaled = scaler.transform(synthetic_data[:len(original_data)])

            # Prepare sequences
            X_real, y_real = prepare_sequences_for_prediction(original_scaled, seq_len, target_idx)
            X_synth, y_synth = prepare_sequences_for_prediction(synthetic_scaled, seq_len, target_idx)

            # Split data
            split = int(0.7 * len(X_real))
            X_train_real, X_test_real = X_real[:split], X_real[split:]
            y_train_real, y_test_real = y_real[:split], y_real[split:]

            # Train on Real, Test on Real (TRTR)
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            model_real = train_lstm_predictor(X_train_real, y_train_real, epochs=30, device=device)
            metrics_trtr = evaluate_lstm_prediction(model_real, X_test_real, y_test_real, device)

            # Train on Synthetic, Test on Real (TSTR)
            train_size = min(len(X_synth), len(X_train_real))
            model_synth = train_lstm_predictor(
                X_synth[:train_size],
                y_synth[:train_size],
                epochs=30,
                device=device
            )
            metrics_tstr = evaluate_lstm_prediction(model_synth, X_test_real, y_test_real, device)

            # Calculate efficacy (how close TSTR is to TRTR)
            efficacy_rmse = 1.0 - min(1.0, abs(metrics_trtr['rmse'] - metrics_tstr['rmse']) / (metrics_trtr['rmse'] + 1e-7))
            efficacy_mae = 1.0 - min(1.0, abs(metrics_trtr['mae'] - metrics_tstr['mae']) / (metrics_trtr['mae'] + 1e-7))

            return {
                'target_column': target_col,
                'model_type': 'LSTM',
                'trtr_rmse': metrics_trtr['rmse'],
                'trtr_mae': metrics_trtr['mae'],
                'tstr_rmse': metrics_tstr['rmse'],
                'tstr_mae': metrics_tstr['mae'],
                'efficacy_rmse': efficacy_rmse,
                'efficacy_mae': efficacy_mae,
                'overall_efficacy': (efficacy_rmse + efficacy_mae) / 2,
                'interpretation': 'EXCELLENT' if efficacy_rmse >= 0.85 else 'GOOD' if efficacy_rmse >= 0.70 else 'MODERATE'
            }

        except Exception as e:
            logger.error(f"LSTM evaluation failed for {target_col}: {e}")
            return None

    def _evaluate_arima_for_column(self, target_col: str) -> Optional[Dict[str, Any]]:
        """Evaluate ARIMA prediction for a specific column"""
        try:
            # Get single column data
            original_series = self.original_df[target_col].dropna().values
            synthetic_series = self.synthetic_df[target_col].dropna().values

            # Check minimum data
            if len(original_series) < 50:
                logger.warning(f"ARIMA: Skipping {target_col} - insufficient data ({len(original_series)} samples)")
                return None

            # Split data
            split = int(0.7 * len(original_series))
            train_real = original_series[:split]
            test_real = original_series[split:]

            train_synth = synthetic_series[:min(len(synthetic_series), split)]

            logger.info(f"ARIMA: Evaluating {target_col} (train={len(train_real)}, test={len(test_real)})")

            # TRTR: Train on Real, Test on Real
            metrics_trtr = evaluate_arima_prediction(train_real, test_real, use_auto=True)

            # TSTR: Train on Synthetic, Test on Real
            metrics_tstr = evaluate_arima_prediction(train_synth, test_real, use_auto=True)

            # Skip if ARIMA failed
            if metrics_trtr['rmse'] == float('inf') or metrics_tstr['rmse'] == float('inf'):
                logger.warning(f"ARIMA: Failed for {target_col} - TRTR RMSE: {metrics_trtr['rmse']}, TSTR RMSE: {metrics_tstr['rmse']}")
                return None

            # Calculate efficacy
            efficacy_rmse = 1.0 - min(1.0, abs(metrics_trtr['rmse'] - metrics_tstr['rmse']) / (metrics_trtr['rmse'] + 1e-7))
            efficacy_mae = 1.0 - min(1.0, abs(metrics_trtr['mae'] - metrics_tstr['mae']) / (metrics_trtr['mae'] + 1e-7))

            result = {
                'target_column': target_col,
                'model_type': 'ARIMA',
                'trtr_rmse': metrics_trtr['rmse'],
                'trtr_mae': metrics_trtr['mae'],
                'tstr_rmse': metrics_tstr['rmse'],
                'tstr_mae': metrics_tstr['mae'],
                'efficacy_rmse': efficacy_rmse,
                'efficacy_mae': efficacy_mae,
                'overall_efficacy': (efficacy_rmse + efficacy_mae) / 2,
                'interpretation': 'EXCELLENT' if efficacy_rmse >= 0.85 else 'GOOD' if efficacy_rmse >= 0.70 else 'MODERATE'
            }

            logger.info(f"ARIMA: Successfully evaluated {target_col} - Overall Efficacy: {result['overall_efficacy']:.2%}, Interpretation: {result['interpretation']}")
            return result

        except Exception as e:
            logger.error(f"ARIMA evaluation failed for {target_col}: {e}", exc_info=True)
            return None
