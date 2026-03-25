import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Terminal, Settings, Sliders } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/Card';
import { Button } from '../components/Button';
import ErrorBanner from '../components/ErrorBanner';
import { generateLogs } from '../services/api';
import { getApiErrorMessage } from '../lib/utils';
import type { LogFormatInfo } from '../types';

const FORMAT_BADGE_COLORS: Record<string, string> = {
  apache: 'bg-red-100 text-red-800',
  nginx: 'bg-green-100 text-green-800',
  syslog: 'bg-blue-100 text-blue-800',
  json: 'bg-purple-100 text-purple-800',
  csv: 'bg-amber-100 text-amber-800',
  custom: 'bg-gray-100 text-gray-800',
};

export default function ConfigureLogs() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const [logInfo, setLogInfo] = useState<LogFormatInfo | null>(null);
  const [numLines, setNumLines] = useState(1000);
  const [timeRangeHours, setTimeRangeHours] = useState(24);
  const [errorRate, setErrorRate] = useState(0.05);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (jobId) {
      const stored = sessionStorage.getItem(`log_info_${jobId}`);
      if (stored) {
        try {
          setLogInfo(JSON.parse(stored));
        } catch {
          // Ignore parse errors
        }
      }
    }
  }, [jobId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!jobId) return;

    setSubmitting(true);
    try {
      await generateLogs(jobId, {
        num_log_lines: numLines,
        log_time_range_hours: timeRangeHours,
        log_error_rate: errorRate,
      });
      navigate(`/generate/${jobId}`);
    } catch (err: unknown) {
      console.error('Generation error:', err);
      setError(getApiErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const detectedFormat = logInfo?.detected_format || 'unknown';
  const badgeClass = FORMAT_BADGE_COLORS[detectedFormat.toLowerCase()] || FORMAT_BADGE_COLORS.custom;

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}
      <div className="mb-8">
        <Button
          variant="outline"
          onClick={() => navigate('/upload')}
          className="mb-4"
        >
          &larr; Back to Upload
        </Button>
        <h1 className="text-3xl font-bold mb-2">Configure Log Generation</h1>
        <p className="text-gray-600">Set up synthetic log data generation parameters</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Detected Format Info */}
        {logInfo && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Terminal className="h-5 w-5 mr-2 text-emerald-600" />
                Detected Log Format
              </CardTitle>
              <CardDescription>
                Summary of the uploaded log file
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-gray-700">Format:</span>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${badgeClass}`}>
                    {detectedFormat}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-gray-700">Total Lines:</span>
                  <span className="text-sm text-gray-900">{logInfo.total_lines?.toLocaleString() ?? 'N/A'}</span>
                </div>
                {logInfo.fields && logInfo.fields.length > 0 && (
                  <div>
                    <span className="text-sm font-medium text-gray-700">Fields:</span>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {logInfo.fields.map((field) => (
                        <span
                          key={field}
                          className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs font-mono"
                        >
                          {field}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Generation Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Sliders className="h-5 w-5 mr-2 text-emerald-600" />
              Generation Settings
            </CardTitle>
            <CardDescription>
              Configure how many log lines to generate and their properties
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Number of Lines */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Number of Lines to Generate
              </label>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min={100}
                  max={100000}
                  step={100}
                  value={numLines}
                  onChange={(e) => setNumLines(Number(e.target.value))}
                  className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-emerald-600"
                />
                <input
                  type="number"
                  min={100}
                  max={100000}
                  value={numLines}
                  onChange={(e) => setNumLines(Math.min(100000, Math.max(100, Number(e.target.value))))}
                  className="w-28 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                />
              </div>
              <p className="text-sm text-gray-500 mt-1">
                Generate {numLines.toLocaleString()} synthetic log lines
              </p>
            </div>

            {/* Time Range */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Time Range (hours)
              </label>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min={1}
                  max={8760}
                  step={1}
                  value={timeRangeHours}
                  onChange={(e) => setTimeRangeHours(Number(e.target.value))}
                  className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-emerald-600"
                />
                <input
                  type="number"
                  min={1}
                  max={8760}
                  value={timeRangeHours}
                  onChange={(e) => setTimeRangeHours(Math.min(8760, Math.max(1, Number(e.target.value))))}
                  className="w-28 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                />
              </div>
              <p className="text-sm text-gray-500 mt-1">
                {timeRangeHours < 24
                  ? `${timeRangeHours} hour${timeRangeHours > 1 ? 's' : ''}`
                  : timeRangeHours < 168
                  ? `${(timeRangeHours / 24).toFixed(1)} days`
                  : `${(timeRangeHours / 168).toFixed(1)} weeks`}
                {' '}of simulated log data
              </p>
            </div>

            {/* Error Rate */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Error Rate
              </label>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.01}
                  value={errorRate}
                  onChange={(e) => setErrorRate(Number(e.target.value))}
                  className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-emerald-600"
                />
                <input
                  type="number"
                  min={0}
                  max={1}
                  step={0.01}
                  value={errorRate}
                  onChange={(e) => setErrorRate(Math.min(1, Math.max(0, Number(e.target.value))))}
                  className="w-28 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                />
              </div>
              <p className="text-sm text-gray-500 mt-1">
                {(errorRate * 100).toFixed(0)}% of generated lines will be error/warning entries
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Info Box */}
        <Card className="bg-emerald-50 border-emerald-200">
          <CardContent className="pt-6">
            <div className="flex items-start">
              <Settings className="h-5 w-5 text-emerald-700 mr-3 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-emerald-900">
                <p className="font-semibold mb-2">How Log Synthesis Works</p>
                <ul className="space-y-1 text-xs">
                  <li>- Analyzes the format and patterns in your uploaded logs</li>
                  <li>- Learns field distributions, severity levels, and temporal patterns</li>
                  <li>- Generates synthetic log entries that match the original structure</li>
                  <li>- Preserves realistic timestamps, IP addresses, and status codes</li>
                  <li>- Injects error entries at the configured rate for testing</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Submit Buttons */}
        <div className="flex gap-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate('/upload')}
            className="flex-1"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={submitting}
            className="flex-1 bg-emerald-600 hover:bg-emerald-700"
          >
            {submitting ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                Starting Generation...
              </>
            ) : (
              'Generate Logs'
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
