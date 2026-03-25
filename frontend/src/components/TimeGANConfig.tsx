import { Clock, TrendingUp, Calendar, Zap, Info } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './Card';

interface TimeSeriesInfo {
  datetime_columns: string[];
  confidence: number;
  temporal_features: string[];
  suggested_datetime_col: string | null;
}

interface TimeGANConfigProps {
  timeseriesInfo: TimeSeriesInfo | null;
  sequenceLength: number;
  datetimeColumn: string;
  onSequenceLengthChange: (value: number) => void;
  onDatetimeColumnChange: (value: string) => void;
}

export default function TimeGANConfig({
  timeseriesInfo,
  sequenceLength,
  datetimeColumn,
  onSequenceLengthChange,
  onDatetimeColumnChange,
}: TimeGANConfigProps) {
  if (!timeseriesInfo) {
    return null;
  }

  const confidencePercent = Math.round(timeseriesInfo.confidence * 100);
  const confidenceColor =
    confidencePercent >= 70
      ? 'text-green-600'
      : confidencePercent >= 40
      ? 'text-yellow-600'
      : 'text-orange-600';

  return (
    <Card className="border-2 border-blue-200 bg-gradient-to-br from-blue-50 to-indigo-50">
      <CardHeader>
        <CardTitle className="flex items-center text-blue-900">
          <Clock className="h-6 w-6 mr-2" />
          Time-Series Configuration (TimeGAN)
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Detection Info */}
        <div className="bg-white p-4 rounded-lg border border-blue-200">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-blue-600" />
              <h3 className="font-semibold text-gray-900">Time-Series Detected</h3>
            </div>
            <span className={`text-sm font-bold ${confidenceColor}`}>
              {confidencePercent}% confidence
            </span>
          </div>

          {timeseriesInfo.datetime_columns.length > 0 && (
            <div className="text-sm text-gray-700 mb-2">
              <span className="font-medium">Datetime Columns:</span>{' '}
              {timeseriesInfo.datetime_columns.join(', ')}
            </div>
          )}

          {timeseriesInfo.temporal_features.length > 0 && (
            <div className="text-sm text-gray-700">
              <span className="font-medium">Temporal Features:</span>{' '}
              {timeseriesInfo.temporal_features.join(', ')}
            </div>
          )}
        </div>

        {/* Sequence Length */}
        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2 flex items-center">
            <Zap className="h-4 w-4 mr-1 text-indigo-600" />
            Sequence Length
          </label>
          <div className="flex items-center gap-4">
            <input
              type="range"
              min="6"
              max="100"
              value={sequenceLength}
              onChange={(e) => onSequenceLengthChange(parseInt(e.target.value))}
              className="flex-1 h-2 bg-blue-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
            <span className="text-2xl font-bold text-blue-600 min-w-[4rem] text-center">
              {sequenceLength}
            </span>
          </div>
          <p className="text-xs text-gray-600 mt-2 flex items-start gap-1">
            <Info className="h-3 w-3 mt-0.5 flex-shrink-0" />
            Number of time steps in each sequence. Longer sequences capture more temporal patterns but require more data and training time.
          </p>
        </div>

        {/* Datetime Column Selector */}
        {timeseriesInfo.datetime_columns.length > 0 && (
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2 flex items-center">
              <Calendar className="h-4 w-4 mr-1 text-indigo-600" />
              Datetime Column
            </label>
            <select
              value={datetimeColumn}
              onChange={(e) => onDatetimeColumnChange(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">-- Select datetime column --</option>
              {timeseriesInfo.datetime_columns.map((col) => (
                <option key={col} value={col}>
                  {col}
                  {col === timeseriesInfo.suggested_datetime_col && ' (recommended)'}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-600 mt-2 flex items-start gap-1">
              <Info className="h-3 w-3 mt-0.5 flex-shrink-0" />
              The column containing timestamp/date information for ordering the time-series data.
            </p>
          </div>
        )}

        {/* Info Box */}
        <div className="bg-blue-100 border border-blue-300 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-blue-700 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-900">
              <p className="font-semibold mb-1">About TimeGAN (PyTorch)</p>
              <p>
                TimeGAN uses a Generative Adversarial Network specifically designed for time-series data. It preserves:
              </p>
              <ul className="list-disc list-inside mt-2 space-y-1 text-xs">
                <li>Temporal dynamics and dependencies</li>
                <li>Sequential patterns and trends</li>
                <li>Statistical properties across time</li>
              </ul>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
