import { Clock, TrendingUp, Activity, BarChart3 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './Card';

interface TimeSeriesMLEfficacy {
  lstm_metrics: Array<{
    target_column: string;
    model_type: string;
    trtr_rmse: number;
    trtr_mae: number;
    tstr_rmse: number;
    tstr_mae: number;
    efficacy_rmse: number;
    efficacy_mae: number;
    overall_efficacy: number;
    interpretation: string;
  }>;
  arima_metrics: Array<{
    target_column: string;
    model_type: string;
    trtr_rmse: number;
    trtr_mae: number;
    tstr_rmse: number;
    tstr_mae: number;
    efficacy_rmse: number;
    efficacy_mae: number;
    overall_efficacy: number;
    interpretation: string;
  }>;
  overall_rmse_ratio: number;
  overall_mae_ratio: number;
  interpretation: string;
}

interface TimeSeriesMetricsProps {
  tsMetrics: TimeSeriesMLEfficacy | null;
}

export default function TimeSeriesMetrics({ tsMetrics }: TimeSeriesMetricsProps) {
  if (!tsMetrics || (!tsMetrics.lstm_metrics?.length && !tsMetrics.arima_metrics?.length)) {
    return null;
  }

  const getInterpretationColor = (interpretation: string) => {
    switch (interpretation) {
      case 'EXCELLENT':
        return 'text-emerald-700';
      case 'GOOD':
        return 'text-blue-700';
      case 'MODERATE':
        return 'text-yellow-700';
      default:
        return 'text-orange-700';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.85) return 'text-emerald-600';
    if (score >= 0.70) return 'text-blue-600';
    if (score >= 0.50) return 'text-yellow-600';
    return 'text-orange-600';
  };

  return (
    <Card className="border-2 border-indigo-200 bg-gradient-to-br from-indigo-50 to-purple-50">
      <CardHeader>
        <CardTitle className="flex items-center text-indigo-900">
          <Clock className="h-6 w-6 mr-2" />
          Time-Series ML Efficacy (LSTM & ARIMA)
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Overall Score */}
        <div className="bg-white p-4 rounded-lg border-2 border-indigo-300">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-gray-900 mb-1">Overall Time-Series Quality</h3>
              <p className="text-sm text-gray-600">Prediction model efficacy on synthetic data</p>
            </div>
            <div className="text-right">
              <div className={`text-3xl font-bold ${getInterpretationColor(tsMetrics.interpretation)}`}>
                {tsMetrics.interpretation}
              </div>
              <div className="text-xs text-gray-600 mt-1">
                RMSE Ratio: {(tsMetrics.overall_rmse_ratio * 100).toFixed(1)}%
              </div>
              <div className="text-xs text-gray-600">
                MAE Ratio: {(tsMetrics.overall_mae_ratio * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </div>

        {/* LSTM Metrics */}
        {tsMetrics.lstm_metrics && tsMetrics.lstm_metrics.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-indigo-600" />
              <h4 className="font-bold text-gray-900">LSTM Predictions ({tsMetrics.lstm_metrics.length})</h4>
            </div>

            {tsMetrics.lstm_metrics.map((metric, idx) => (
              <div key={idx} className="bg-white p-4 rounded-lg border border-indigo-200">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h5 className="font-semibold text-gray-900">{metric.target_column}</h5>
                    <span className="text-xs text-gray-600">Neural Network Time-Series Forecasting</span>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-sm font-bold ${getInterpretationColor(metric.interpretation)} bg-opacity-10`}>
                    {metric.interpretation}
                  </span>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">TRTR RMSE:</span>
                    <div className="font-bold text-blue-700">{metric.trtr_rmse.toFixed(4)}</div>
                  </div>
                  <div>
                    <span className="text-gray-600">TSTR RMSE:</span>
                    <div className="font-bold text-purple-700">{metric.tstr_rmse.toFixed(4)}</div>
                  </div>
                  <div>
                    <span className="text-gray-600">TRTR MAE:</span>
                    <div className="font-bold text-blue-700">{metric.trtr_mae.toFixed(4)}</div>
                  </div>
                  <div>
                    <span className="text-gray-600">TSTR MAE:</span>
                    <div className="font-bold text-purple-700">{metric.tstr_mae.toFixed(4)}</div>
                  </div>
                </div>

                <div className="mt-3 pt-3 border-t border-gray-200 flex items-center justify-between">
                  <div className="text-sm">
                    <span className="text-gray-600">RMSE Efficacy:</span>
                    <span className={`ml-2 font-bold ${getScoreColor(metric.efficacy_rmse)}`}>
                      {(metric.efficacy_rmse * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="text-sm">
                    <span className="text-gray-600">MAE Efficacy:</span>
                    <span className={`ml-2 font-bold ${getScoreColor(metric.efficacy_mae)}`}>
                      {(metric.efficacy_mae * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="text-sm">
                    <span className="text-gray-600">Overall:</span>
                    <span className={`ml-2 font-bold ${getScoreColor(metric.overall_efficacy)}`}>
                      {(metric.overall_efficacy * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ARIMA Metrics */}
        {tsMetrics.arima_metrics && tsMetrics.arima_metrics.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-indigo-600" />
              <h4 className="font-bold text-gray-900">ARIMA Predictions ({tsMetrics.arima_metrics.length})</h4>
            </div>

            {tsMetrics.arima_metrics.map((metric, idx) => (
              <div key={idx} className="bg-white p-4 rounded-lg border border-indigo-200">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h5 className="font-semibold text-gray-900">{metric.target_column}</h5>
                    <span className="text-xs text-gray-600">Autoregressive Integrated Moving Average</span>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-sm font-bold ${getInterpretationColor(metric.interpretation)} bg-opacity-10`}>
                    {metric.interpretation}
                  </span>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">TRTR RMSE:</span>
                    <div className="font-bold text-blue-700">{metric.trtr_rmse.toFixed(4)}</div>
                  </div>
                  <div>
                    <span className="text-gray-600">TSTR RMSE:</span>
                    <div className="font-bold text-purple-700">{metric.tstr_rmse.toFixed(4)}</div>
                  </div>
                  <div>
                    <span className="text-gray-600">TRTR MAE:</span>
                    <div className="font-bold text-blue-700">{metric.trtr_mae.toFixed(4)}</div>
                  </div>
                  <div>
                    <span className="text-gray-600">TSTR MAE:</span>
                    <div className="font-bold text-purple-700">{metric.tstr_mae.toFixed(4)}</div>
                  </div>
                </div>

                <div className="mt-3 pt-3 border-t border-gray-200 flex items-center justify-between">
                  <div className="text-sm">
                    <span className="text-gray-600">RMSE Efficacy:</span>
                    <span className={`ml-2 font-bold ${getScoreColor(metric.efficacy_rmse)}`}>
                      {(metric.efficacy_rmse * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="text-sm">
                    <span className="text-gray-600">MAE Efficacy:</span>
                    <span className={`ml-2 font-bold ${getScoreColor(metric.efficacy_mae)}`}>
                      {(metric.efficacy_mae * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="text-sm">
                    <span className="text-gray-600">Overall:</span>
                    <span className={`ml-2 font-bold ${getScoreColor(metric.overall_efficacy)}`}>
                      {(metric.overall_efficacy * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Info Box */}
        <div className="bg-indigo-100 border border-indigo-300 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <BarChart3 className="h-5 w-5 text-indigo-700 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-indigo-900">
              <p className="font-semibold mb-1">TRTR vs TSTR Evaluation</p>
              <ul className="text-xs space-y-1">
                <li>• <strong>TRTR</strong> (Train Real, Test Real): Baseline model performance</li>
                <li>• <strong>TSTR</strong> (Train Synthetic, Test Real): Synthetic data quality</li>
                <li>• <strong>RMSE</strong>: Root Mean Squared Error (lower is better)</li>
                <li>• <strong>MAE</strong>: Mean Absolute Error (lower is better)</li>
                <li>• <strong>Efficacy</strong>: How close TSTR is to TRTR (higher is better)</li>
              </ul>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
