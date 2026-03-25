import { useState, useEffect } from 'react';
import { Terminal, Download } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './Card';
import { Button } from './Button';
import { getLogResults, downloadLogs } from '../services/api';
import { getApiErrorMessage } from '../lib/utils';
import type { LogResultsResponse } from '../types';

interface LogResultsDashboardProps {
  jobId: string;
}

const FORMAT_BADGE_COLORS: Record<string, string> = {
  apache: 'bg-red-100 text-red-800',
  nginx: 'bg-green-100 text-green-800',
  syslog: 'bg-blue-100 text-blue-800',
  json: 'bg-purple-100 text-purple-800',
  csv: 'bg-amber-100 text-amber-800',
  custom: 'bg-gray-100 text-gray-800',
};

export default function LogResultsDashboard({ jobId }: LogResultsDashboardProps) {
  const [results, setResults] = useState<LogResultsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchResults();
  }, [jobId]);

  const fetchResults = async () => {
    try {
      const data = await getLogResults(jobId);
      setResults(data);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    window.open(downloadLogs(jobId), '_blank');
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="text-center text-gray-600">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600 mx-auto mb-4" />
            <p>Loading log results...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-red-200 bg-red-50">
        <CardContent className="py-8">
          <div className="text-center text-red-600">
            <p className="font-medium">Error loading results</p>
            <p className="text-sm mt-1">{error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!results) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="text-center text-gray-600">
            <p>No log results available</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const { summary, analysis, sample_logs } = results;
  const detectedFormat = summary.format || 'unknown';
  const badgeClass = FORMAT_BADGE_COLORS[detectedFormat.toLowerCase()] || FORMAT_BADGE_COLORS.custom;

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-emerald-600">
              {summary.original_lines?.toLocaleString() ?? 'N/A'}
            </div>
            <div className="text-sm text-gray-600">Original Lines</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-blue-600">
              {summary.generated_lines?.toLocaleString() ?? 'N/A'}
            </div>
            <div className="text-sm text-gray-600">Generated Lines</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-purple-600">
              {summary.time_range_hours != null
                ? summary.time_range_hours < 24
                  ? `${summary.time_range_hours}h`
                  : `${(summary.time_range_hours / 24).toFixed(1)}d`
                : 'N/A'}
            </div>
            <div className="text-sm text-gray-600">Time Range</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-amber-600">
              {summary.error_rate != null ? `${(summary.error_rate * 100).toFixed(1)}%` : 'N/A'}
            </div>
            <div className="text-sm text-gray-600">Error Rate</div>
          </CardContent>
        </Card>
      </div>

      {/* Detected Format */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Terminal className="h-5 w-5 mr-2 text-emerald-600" />
            Log Format
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-gray-700">Detected Format:</span>
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${badgeClass}`}>
              {detectedFormat}
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Field Distributions */}
      {analysis && Object.keys(analysis).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Field Distributions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {Object.entries(analysis).map(([fieldName, fieldData]) => {
                const data = fieldData as Record<string, unknown>;
                return (
                  <div key={fieldName} className="border rounded-lg p-4">
                    <h4 className="font-mono font-medium text-sm text-gray-900 mb-2">{fieldName}</h4>
                    {typeof data === 'object' && data !== null ? (
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                        {Object.entries(data).map(([key, value]) => (
                          <div key={key} className="flex justify-between text-xs bg-gray-50 rounded px-2 py-1">
                            <span className="text-gray-600 truncate mr-2">{String(key)}</span>
                            <span className="font-medium text-gray-900">
                              {typeof value === 'number'
                                ? Number.isInteger(value)
                                  ? value.toLocaleString()
                                  : value.toFixed(3)
                                : String(value)}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-gray-600">{String(data)}</p>
                    )}
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Sample Log Lines */}
      {sample_logs && sample_logs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Sample Generated Logs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="bg-gray-900 rounded-lg p-4 max-h-96 overflow-auto">
              <pre className="text-xs text-green-400 font-mono whitespace-pre-wrap break-all leading-relaxed">
                {sample_logs.map((line, index) => (
                  <div key={index} className="hover:bg-gray-800 px-1 rounded">
                    {line}
                  </div>
                ))}
              </pre>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Showing {sample_logs.length} sample line{sample_logs.length !== 1 ? 's' : ''} from generated output
            </p>
          </CardContent>
        </Card>
      )}

      {/* Download */}
      <Card>
        <CardContent className="p-6">
          <Button
            onClick={handleDownload}
            className="w-full bg-emerald-600 hover:bg-emerald-700"
          >
            <Download className="h-4 w-4 mr-2" />
            Download Generated Logs
          </Button>
          <p className="text-xs text-gray-500 text-center mt-2">
            Download the complete synthetic log file
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
