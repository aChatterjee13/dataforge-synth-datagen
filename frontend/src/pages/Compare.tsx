import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeftRight, Upload, Loader2, ArrowLeft } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/Card';
import { Button } from '../components/Button';
import { compareDatasets } from '../services/api';
import { getApiErrorMessage } from '../lib/utils';
import type { ValidationResponse } from '../types';

export default function Compare() {
  const navigate = useNavigate();
  const [file1, setFile1] = useState<File | null>(null);
  const [file2, setFile2] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<ValidationResponse | null>(null);

  const acceptedExtensions = '.csv,.xlsx,.xls';

  const handleDrop = useCallback(
    (setter: (file: File | null) => void) => (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile) {
        const ext = droppedFile.name.split('.').pop()?.toLowerCase();
        if (ext === 'csv' || ext === 'xlsx' || ext === 'xls') {
          setter(droppedFile);
          setError(null);
        } else {
          setError('Please upload a CSV, XLSX, or XLS file.');
        }
      }
    },
    []
  );

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleFileChange = (setter: (file: File | null) => void) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0] || null;
    if (selectedFile) {
      setter(selectedFile);
      setError(null);
    }
  };

  const handleCompare = async () => {
    if (!file1 || !file2) {
      setError('Please upload both datasets before comparing.');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const response = await compareDatasets(file1, file2);
      setResults(response);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number): string => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreBgColor = (score: number): string => {
    if (score >= 0.8) return 'bg-green-600';
    if (score >= 0.6) return 'bg-yellow-600';
    return 'bg-red-600';
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      {/* Header */}
      <div className="mb-8">
        <Button variant="ghost" onClick={() => navigate('/')} className="mb-4">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Home
        </Button>
        <div className="flex items-center gap-3">
          <ArrowLeftRight className="h-8 w-8 text-blue-600" />
          <div>
            <h1 className="text-3xl font-bold">Compare Datasets</h1>
            <p className="text-gray-600">Upload two datasets to compare their statistical properties</p>
          </div>
        </div>
      </div>

      {/* Upload Areas */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Baseline Dataset */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Baseline Dataset</CardTitle>
          </CardHeader>
          <CardContent>
            <div
              onDrop={handleDrop(setFile1)}
              onDragOver={handleDragOver}
              className={`
                border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
                ${file1 ? 'border-green-400 bg-green-50' : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50'}
              `}
            >
              <input
                type="file"
                accept={acceptedExtensions}
                onChange={handleFileChange(setFile1)}
                className="hidden"
                id="file1-upload"
              />
              <label htmlFor="file1-upload" className="cursor-pointer">
                {file1 ? (
                  <div className="flex flex-col items-center">
                    <Upload className="h-10 w-10 text-green-500 mb-3" />
                    <p className="font-medium text-green-700">{file1.name}</p>
                    <p className="text-sm text-gray-500 mt-1">
                      {(file1.size / 1024).toFixed(1)} KB
                    </p>
                    <p className="text-xs text-gray-400 mt-2">Click or drop to replace</p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center">
                    <Upload className="h-10 w-10 text-gray-400 mb-3" />
                    <p className="text-gray-700 font-medium mb-1">Drag & drop or browse</p>
                    <p className="text-gray-400 text-xs">CSV, XLSX, XLS</p>
                  </div>
                )}
              </label>
            </div>
          </CardContent>
        </Card>

        {/* Comparison Dataset */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Comparison Dataset</CardTitle>
          </CardHeader>
          <CardContent>
            <div
              onDrop={handleDrop(setFile2)}
              onDragOver={handleDragOver}
              className={`
                border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
                ${file2 ? 'border-green-400 bg-green-50' : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50'}
              `}
            >
              <input
                type="file"
                accept={acceptedExtensions}
                onChange={handleFileChange(setFile2)}
                className="hidden"
                id="file2-upload"
              />
              <label htmlFor="file2-upload" className="cursor-pointer">
                {file2 ? (
                  <div className="flex flex-col items-center">
                    <Upload className="h-10 w-10 text-green-500 mb-3" />
                    <p className="font-medium text-green-700">{file2.name}</p>
                    <p className="text-sm text-gray-500 mt-1">
                      {(file2.size / 1024).toFixed(1)} KB
                    </p>
                    <p className="text-xs text-gray-400 mt-2">Click or drop to replace</p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center">
                    <Upload className="h-10 w-10 text-gray-400 mb-3" />
                    <p className="text-gray-700 font-medium mb-1">Drag & drop or browse</p>
                    <p className="text-gray-400 text-xs">CSV, XLSX, XLS</p>
                  </div>
                )}
              </label>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Compare Button */}
      <div className="flex justify-center mb-8">
        <Button
          onClick={handleCompare}
          size="lg"
          disabled={!file1 || !file2 || loading}
          className="px-12"
        >
          {loading ? (
            <>
              <Loader2 className="h-5 w-5 mr-2 animate-spin" />
              Comparing...
            </>
          ) : (
            <>
              <ArrowLeftRight className="h-5 w-5 mr-2" />
              Compare
            </>
          )}
        </Button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800 font-medium">Error</p>
          <p className="text-red-600 text-sm">{error}</p>
        </div>
      )}

      {/* Results */}
      {results && (
        <div className="space-y-6">
          {/* Score Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Quality Score */}
            <Card>
              <CardContent className="p-6">
                <div className="text-center">
                  <p className="text-sm font-medium text-gray-600 mb-2">Quality Score</p>
                  <div className={`text-5xl font-bold mb-2 ${getScoreColor(results.metrics.quality_score)}`}>
                    {Math.round(results.metrics.quality_score * 100)}%
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mt-3">
                    <div
                      className={`h-2 rounded-full ${getScoreBgColor(results.metrics.quality_score)}`}
                      style={{ width: `${Math.round(results.metrics.quality_score * 100)}%` }}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Correlation Preservation */}
            <Card>
              <CardContent className="p-6">
                <div className="text-center">
                  <p className="text-sm font-medium text-gray-600 mb-2">Correlation Preservation</p>
                  <div className={`text-5xl font-bold mb-2 ${getScoreColor(results.metrics.correlation_preservation)}`}>
                    {Math.round(results.metrics.correlation_preservation * 100)}%
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mt-3">
                    <div
                      className={`h-2 rounded-full ${getScoreBgColor(results.metrics.correlation_preservation)}`}
                      style={{ width: `${Math.round(results.metrics.correlation_preservation * 100)}%` }}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Privacy Score */}
            <Card>
              <CardContent className="p-6">
                <div className="text-center">
                  <p className="text-sm font-medium text-gray-600 mb-2">Privacy Score</p>
                  <div className={`text-5xl font-bold mb-2 ${getScoreColor(results.metrics.privacy_score)}`}>
                    {Math.round(results.metrics.privacy_score * 100)}%
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mt-3">
                    <div
                      className={`h-2 rounded-full ${getScoreBgColor(results.metrics.privacy_score)}`}
                      style={{ width: `${Math.round(results.metrics.privacy_score * 100)}%` }}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Column-Level Quality Table */}
          {results.metrics.column_metrics && Object.keys(results.metrics.column_metrics).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Column-Level Quality</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b-2 border-gray-300">
                        <th className="text-left py-3 px-4">Column Name</th>
                        <th className="text-left py-3 px-4">Type</th>
                        <th className="text-right py-3 px-4">Quality Score</th>
                        <th className="text-right py-3 px-4">KS Statistic</th>
                        <th className="text-right py-3 px-4">P-Value</th>
                        <th className="text-right py-3 px-4">JS Divergence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(results.metrics.column_metrics).map(([colName, colMetrics]) => (
                        <tr key={colName} className="border-b border-gray-200 hover:bg-gray-50">
                          <td className="py-3 px-4 font-medium">{colName}</td>
                          <td className="py-3 px-4">
                            <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${
                              colMetrics.column_type === 'numeric'
                                ? 'bg-blue-100 text-blue-800'
                                : 'bg-purple-100 text-purple-800'
                            }`}>
                              {colMetrics.column_type}
                            </span>
                          </td>
                          <td className="text-right py-3 px-4">
                            <span className={`font-semibold ${getScoreColor(colMetrics.quality_score)}`}>
                              {Math.round(colMetrics.quality_score * 100)}%
                            </span>
                          </td>
                          <td className="text-right py-3 px-4 text-gray-600">
                            {colMetrics.ks_statistic !== undefined
                              ? colMetrics.ks_statistic.toFixed(4)
                              : colMetrics.chi2_statistic !== undefined
                              ? colMetrics.chi2_statistic.toFixed(4)
                              : '-'}
                          </td>
                          <td className="text-right py-3 px-4 text-gray-600">
                            {colMetrics.ks_pvalue !== undefined
                              ? colMetrics.ks_pvalue.toFixed(4)
                              : '-'}
                          </td>
                          <td className="text-right py-3 px-4 text-gray-600">
                            {colMetrics.js_divergence !== undefined
                              ? colMetrics.js_divergence.toFixed(4)
                              : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Assessment Summary */}
          {results.assessment_summary && (
            <Card>
              <CardHeader>
                <CardTitle>Assessment Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-gray-50 rounded-lg p-4">
                  <pre className="whitespace-pre-wrap text-sm text-gray-700 font-sans leading-relaxed">
                    {results.assessment_summary}
                  </pre>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
