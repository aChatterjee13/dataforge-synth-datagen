import { useState, useEffect } from 'react';
import { ShieldCheck, Download, Eye, EyeOff } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './Card';
import { Button } from './Button';
import { getPIIResults, downloadPIIMasked } from '../services/api';
import { getApiErrorMessage } from '../lib/utils';
import type { PIIResultsResponse } from '../types';

interface PIIResultsDashboardProps {
  jobId: string;
}

export default function PIIResultsDashboard({ jobId }: PIIResultsDashboardProps) {
  const [results, setResults] = useState<PIIResultsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [visibleColumns, setVisibleColumns] = useState<Set<string>>(new Set());

  useEffect(() => {
    const fetchResults = async () => {
      try {
        const data = await getPIIResults(jobId);
        setResults(data);
      } catch (err: unknown) {
        setError(getApiErrorMessage(err));
      } finally {
        setLoading(false);
      }
    };

    fetchResults();
  }, [jobId]);

  const toggleColumnVisibility = (columnName: string) => {
    setVisibleColumns((prev) => {
      const next = new Set(prev);
      if (next.has(columnName)) {
        next.delete(columnName);
      } else {
        next.add(columnName);
      }
      return next;
    });
  };

  const handleDownload = () => {
    window.open(downloadPIIMasked(jobId), '_blank');
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="text-center text-gray-600">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600 mx-auto mb-4" />
            <p>Loading PII masking results...</p>
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
            <p>No PII masking results available</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const summary = results.summary as Record<string, any>;
  const privacyAssessment = results.privacy_assessment as Record<string, any>;
  const columnReports = results.column_reports || [];

  // Compute strategy breakdown
  const strategyBreakdown: Record<string, number> = {};
  columnReports.forEach((report) => {
    const strategy = report.strategy || 'unknown';
    strategyBreakdown[strategy] = (strategyBreakdown[strategy] || 0) + 1;
  });

  const strategyColors: Record<string, string> = {
    synthetic: 'bg-blue-100 text-blue-800',
    hash: 'bg-purple-100 text-purple-800',
    redact: 'bg-red-100 text-red-800',
    generalize: 'bg-amber-100 text-amber-800',
  };

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-gray-800">
              {summary.total_columns ?? columnReports.length + (summary.non_pii_columns ?? 0)}
            </div>
            <div className="text-sm text-gray-600">Total Columns</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-emerald-600">
              {summary.pii_columns_detected ?? columnReports.length}
            </div>
            <div className="text-sm text-gray-600">PII Columns Detected</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-blue-600">
              {summary.rows_processed ?? '--'}
            </div>
            <div className="text-sm text-gray-600">Rows Processed</div>
          </CardContent>
        </Card>
      </div>

      {/* Strategy Breakdown */}
      {Object.keys(strategyBreakdown).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <ShieldCheck className="h-5 w-5 mr-2 text-emerald-600" />
              Strategy Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-3">
              {Object.entries(strategyBreakdown).map(([strategy, count]) => (
                <div
                  key={strategy}
                  className="flex items-center gap-2 px-4 py-2 bg-gray-50 rounded-lg border border-gray-200"
                >
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium capitalize ${
                      strategyColors[strategy] || 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {strategy}
                  </span>
                  <span className="text-sm font-bold text-gray-800">{count}</span>
                  <span className="text-xs text-gray-500">
                    column{count !== 1 ? 's' : ''}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Before/After Comparison */}
      {columnReports.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Before / After Comparison</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {columnReports.map((report) => {
                const isVisible = visibleColumns.has(report.column_name);

                return (
                  <div
                    key={report.column_name}
                    className="border border-gray-200 rounded-lg overflow-hidden"
                  >
                    <div className="flex items-center justify-between p-3 bg-gray-50">
                      <div className="flex items-center gap-3">
                        <span className="font-mono font-medium text-sm text-gray-900">
                          {report.column_name}
                        </span>
                        <span className="px-2 py-0.5 bg-purple-100 text-purple-800 rounded text-xs font-medium">
                          {report.pii_type}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-medium capitalize ${
                            strategyColors[report.strategy] || 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {report.strategy}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-medium ${
                            report.confidence >= 0.9
                              ? 'bg-green-100 text-green-800'
                              : report.confidence >= 0.7
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {(report.confidence * 100).toFixed(0)}% conf
                        </span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleColumnVisibility(report.column_name)}
                      >
                        {isVisible ? (
                          <EyeOff className="h-4 w-4 text-gray-500" />
                        ) : (
                          <Eye className="h-4 w-4 text-gray-500" />
                        )}
                      </Button>
                    </div>

                    {isVisible && (
                      <div className="p-3">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-gray-100">
                              <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 w-12">
                                #
                              </th>
                              <th className="text-left py-2 px-3 text-xs font-medium text-red-600">
                                Before (Original)
                              </th>
                              <th className="text-left py-2 px-3 text-xs font-medium text-green-600">
                                After (Masked)
                              </th>
                            </tr>
                          </thead>
                          <tbody>
                            {report.before_samples.map((before, i) => (
                              <tr key={i} className="border-b border-gray-50">
                                <td className="py-1.5 px-3 text-xs text-gray-400">
                                  {i + 1}
                                </td>
                                <td className="py-1.5 px-3 font-mono text-xs text-red-700 bg-red-50">
                                  {before}
                                </td>
                                <td className="py-1.5 px-3 font-mono text-xs text-green-700 bg-green-50">
                                  {report.after_samples[i] ?? '--'}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Privacy Assessment */}
      {privacyAssessment && Object.keys(privacyAssessment).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <ShieldCheck className="h-5 w-5 mr-2 text-emerald-600" />
              Privacy Assessment
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {Object.entries(privacyAssessment).map(([key, value]) => {
                const displayLabel = key
                  .replace(/_/g, ' ')
                  .replace(/\b\w/g, (c) => c.toUpperCase());

                let displayValue: string;
                if (typeof value === 'number') {
                  displayValue =
                    value <= 1 && value >= 0
                      ? `${(value * 100).toFixed(1)}%`
                      : String(value.toFixed ? value.toFixed(2) : value);
                } else {
                  displayValue = String(value);
                }

                const scoreColor =
                  typeof value === 'number' && value >= 0 && value <= 1
                    ? value >= 0.8
                      ? 'text-green-600'
                      : value >= 0.6
                      ? 'text-amber-600'
                      : 'text-red-600'
                    : 'text-gray-800';

                return (
                  <div
                    key={key}
                    className="p-3 bg-gray-50 rounded-lg border border-gray-200 text-center"
                  >
                    <div className={`text-xl font-bold ${scoreColor}`}>
                      {displayValue}
                    </div>
                    <div className="text-xs text-gray-600 mt-1">{displayLabel}</div>
                  </div>
                );
              })}
            </div>
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
            Download Masked Dataset
          </Button>
          <p className="text-xs text-gray-500 text-center mt-2">
            Download the fully masked dataset with all PII columns transformed
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
