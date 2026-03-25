import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, Upload, Loader2, AlertTriangle, CheckCircle, ArrowLeft, Brain, TrendingDown, BarChart3, GitBranch } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/Card';
import { Button } from '../components/Button';
import { detectDrift, getDriftColumns } from '../services/api';
import { getApiErrorMessage } from '../lib/utils';
import type { DriftResult, ColumnDriftResult, ConceptDriftResult, DriftColumnInfo } from '../types';

export default function DriftDetection() {
  const navigate = useNavigate();
  const [baseline, setBaseline] = useState<File | null>(null);
  const [snapshot, setSnapshot] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<DriftResult | null>(null);

  // Concept drift state
  const [columns, setColumns] = useState<DriftColumnInfo[]>([]);
  const [targetColumn, setTargetColumn] = useState<string>('');
  const [loadingColumns, setLoadingColumns] = useState(false);

  const acceptedExtensions = '.csv,.xlsx,.xls';

  const fetchColumns = useCallback(async (file: File) => {
    setLoadingColumns(true);
    try {
      const cols = await getDriftColumns(file);
      setColumns(cols);
      setTargetColumn('');
    } catch {
      setColumns([]);
    } finally {
      setLoadingColumns(false);
    }
  }, []);

  const handleBaselineSet = useCallback((file: File | null) => {
    setBaseline(file);
    setResults(null);
    setTargetColumn('');
    if (file) {
      fetchColumns(file);
    } else {
      setColumns([]);
    }
  }, [fetchColumns]);

  const handleDrop = useCallback(
    (setter: (file: File | null) => void, isBaseline: boolean) => (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile) {
        const ext = droppedFile.name.split('.').pop()?.toLowerCase();
        if (ext === 'csv' || ext === 'xlsx' || ext === 'xls') {
          if (isBaseline) {
            handleBaselineSet(droppedFile);
          } else {
            setter(droppedFile);
          }
          setError(null);
        } else {
          setError('Please upload a CSV, XLSX, or XLS file.');
        }
      }
    },
    [handleBaselineSet]
  );

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleFileChange = (setter: (file: File | null) => void, isBaseline: boolean) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0] || null;
    if (selectedFile) {
      if (isBaseline) {
        handleBaselineSet(selectedFile);
      } else {
        setter(selectedFile);
      }
      setError(null);
    }
  };

  const handleDetectDrift = async () => {
    if (!baseline || !snapshot) {
      setError('Please upload both the baseline dataset and production snapshot.');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const response = await detectDrift(baseline, snapshot, targetColumn || undefined);
      setResults(response);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const getAlertIcon = (level: string) => {
    switch (level) {
      case 'green':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'yellow':
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      case 'red':
        return (
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-red-500">
            <span className="h-2.5 w-2.5 rounded-full bg-white" />
          </span>
        );
      default:
        return null;
    }
  };

  const getAlertBadgeClasses = (level: string): string => {
    switch (level) {
      case 'green':
        return 'bg-green-100 text-green-800';
      case 'yellow':
        return 'bg-yellow-100 text-yellow-800';
      case 'red':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getDriftScoreColor = (score: number): string => {
    if (score <= 0.2) return 'text-green-600';
    if (score <= 0.5) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getDriftBarColor = (score: number): string => {
    if (score <= 0.2) return 'bg-green-500';
    if (score <= 0.5) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getConceptScoreColor = (score: number): string => {
    if (score <= 0.1) return 'text-green-600';
    if (score <= 0.3) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getConceptBarColor = (score: number): string => {
    if (score <= 0.1) return 'bg-green-500';
    if (score <= 0.3) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const renderConceptDrift = (cd: ConceptDriftResult) => {
    const metricLabel = cd.task_type === 'classification' ? 'Accuracy' : 'R2 Score';
    const pred = cd.prediction_drift;
    const imp = cd.feature_importance_shift;
    const cond = cd.conditional_distribution_shift;

    return (
      <div className="space-y-6">
        {/* Section Header */}
        <div className="flex items-center gap-3 pt-4">
          <Brain className="h-7 w-7 text-indigo-600" />
          <div>
            <h2 className="text-2xl font-bold">Concept Drift Analysis</h2>
            <p className="text-gray-600 text-sm">
              Analyzing relationship changes between features and target: <span className="font-semibold text-indigo-700">{cd.target_column}</span>
            </p>
          </div>
        </div>

        {/* Overall Concept Drift Score */}
        <Card className="border-indigo-200">
          <CardContent className="p-6">
            <div className="text-center">
              <p className="text-sm font-medium text-gray-600 mb-2">Overall Concept Drift Score</p>
              <div className={`text-6xl font-bold mb-3 ${getConceptScoreColor(cd.overall_concept_drift_score)}`}>
                {Math.round(cd.overall_concept_drift_score * 100)}%
              </div>
              <div className="w-full max-w-md mx-auto bg-gray-200 rounded-full h-3">
                <div
                  className={`h-3 rounded-full transition-all ${getConceptBarColor(cd.overall_concept_drift_score)}`}
                  style={{ width: `${Math.max(Math.round(cd.overall_concept_drift_score * 100), 2)}%` }}
                />
              </div>
              <div className="mt-3">
                <span className={`inline-flex px-3 py-1 rounded-full text-sm font-semibold ${
                  cd.concept_drift_detected
                    ? 'bg-red-100 text-red-800'
                    : 'bg-green-100 text-green-800'
                }`}>
                  {cd.concept_drift_detected ? 'Concept Drift Detected' : 'No Concept Drift'}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Three Technique Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1: Prediction Accuracy */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <TrendingDown className="h-4 w-4 text-blue-600" />
                Prediction Drift
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Baseline {metricLabel}</span>
                  <span className="font-semibold">{(pred.baseline_score * 100).toFixed(1)}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Snapshot {metricLabel}</span>
                  <span className="font-semibold">{(pred.snapshot_score * 100).toFixed(1)}%</span>
                </div>
                <div className="border-t pt-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">{metricLabel} Drop</span>
                    <span className={`font-bold ${
                      pred.accuracy_drop > 0.15 ? 'text-red-600' :
                      pred.accuracy_drop > 0.05 ? 'text-yellow-600' : 'text-green-600'
                    }`}>
                      {pred.accuracy_drop > 0 ? '-' : '+'}{Math.abs(pred.accuracy_drop * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
                <div className="flex items-center justify-between pt-1">
                  <span className="text-xs text-gray-500">{pred.model_used}</span>
                  <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${getAlertBadgeClasses(pred.alert_level)}`}>
                    {pred.alert_level.charAt(0).toUpperCase() + pred.alert_level.slice(1)}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Card 2: Feature Importance Shift */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-purple-600" />
                Importance Shift
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Rank Correlation</span>
                  <span className="font-semibold">{imp.rank_correlation.toFixed(3)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Cosine Similarity</span>
                  <span className="font-semibold">{imp.cosine_similarity.toFixed(3)}</span>
                </div>
                <div className="border-t pt-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Drift Score</span>
                    <span className={`font-bold ${getConceptScoreColor(imp.importance_drift_score)}`}>
                      {(imp.importance_drift_score * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
                {/* Top features comparison */}
                <div className="border-t pt-2 space-y-1">
                  <p className="text-xs font-medium text-gray-500">Top Features</p>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <p className="text-gray-400 mb-1">Baseline</p>
                      {imp.baseline_top_features.slice(0, 3).map((f) => (
                        <div key={f.feature_name} className="flex justify-between">
                          <span className="truncate mr-1">{f.feature_name}</span>
                          <span className="text-gray-500">{(f.importance * 100).toFixed(0)}%</span>
                        </div>
                      ))}
                    </div>
                    <div>
                      <p className="text-gray-400 mb-1">Snapshot</p>
                      {imp.snapshot_top_features.slice(0, 3).map((f) => (
                        <div key={f.feature_name} className="flex justify-between">
                          <span className="truncate mr-1">{f.feature_name}</span>
                          <span className="text-gray-500">{(f.importance * 100).toFixed(0)}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
                <div className="flex justify-end pt-1">
                  <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${getAlertBadgeClasses(imp.alert_level)}`}>
                    {imp.alert_level.charAt(0).toUpperCase() + imp.alert_level.slice(1)}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Card 3: Conditional Distribution Shift */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <GitBranch className="h-4 w-4 text-orange-600" />
                Conditional Drift
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Overall Score</span>
                  <span className={`font-bold ${getConceptScoreColor(cond.overall_conditional_drift_score)}`}>
                    {(cond.overall_conditional_drift_score * 100).toFixed(1)}%
                  </span>
                </div>
                {cond.most_drifted_features.length > 0 && (
                  <div className="border-t pt-2">
                    <p className="text-xs font-medium text-gray-500 mb-2">Most Drifted Features</p>
                    <div className="space-y-1">
                      {cond.most_drifted_features.map((f) => {
                        const feat = cond.features.find((x) => x.feature_name === f);
                        return (
                          <div key={f} className="flex items-center justify-between text-sm">
                            <span className="truncate mr-2">{f}</span>
                            <div className="flex items-center gap-2">
                              <span className={`font-semibold ${getDriftScoreColor(feat?.conditional_drift_score ?? 0)}`}>
                                {((feat?.conditional_drift_score ?? 0) * 100).toFixed(1)}%
                              </span>
                              {feat && getAlertIcon(feat.alert_level)}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
                {/* Remaining features summary */}
                {cond.features.length > 3 && (
                  <p className="text-xs text-gray-400 pt-1">
                    + {cond.features.length - 3} more features analyzed
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Conditional Drift Detail Table */}
        {cond.features.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Per-Feature Conditional Drift</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b-2 border-gray-300">
                      <th className="text-left py-3 px-4">Feature</th>
                      <th className="text-right py-3 px-4">Conditional Drift Score</th>
                      <th className="text-center py-3 px-4">Alert Level</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cond.features.map((feat) => (
                      <tr key={feat.feature_name} className="border-b border-gray-200 hover:bg-gray-50">
                        <td className="py-3 px-4 font-medium">{feat.feature_name}</td>
                        <td className="text-right py-3 px-4">
                          <span className={`font-semibold ${getDriftScoreColor(feat.conditional_drift_score)}`}>
                            {(feat.conditional_drift_score * 100).toFixed(1)}%
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex items-center justify-center gap-2">
                            {getAlertIcon(feat.alert_level)}
                            <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${getAlertBadgeClasses(feat.alert_level)}`}>
                              {feat.alert_level.charAt(0).toUpperCase() + feat.alert_level.slice(1)}
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Concept Drift Summary */}
        {cd.summary && (
          <Card className="border-indigo-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Brain className="h-5 w-5 text-indigo-600" />
                Concept Drift Summary
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="bg-indigo-50 rounded-lg p-4">
                <pre className="whitespace-pre-wrap text-sm text-gray-700 font-sans leading-relaxed">
                  {cd.summary}
                </pre>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    );
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
          <Activity className="h-8 w-8 text-purple-600" />
          <div>
            <h1 className="text-3xl font-bold">Data Drift Detection</h1>
            <p className="text-gray-600">Compare a baseline dataset against a production snapshot to detect distribution drift</p>
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
              onDrop={handleDrop(setBaseline, true)}
              onDragOver={handleDragOver}
              className={`
                border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
                ${baseline ? 'border-green-400 bg-green-50' : 'border-gray-300 hover:border-purple-400 hover:bg-purple-50'}
              `}
            >
              <input
                type="file"
                accept={acceptedExtensions}
                onChange={handleFileChange(setBaseline, true)}
                className="hidden"
                id="baseline-upload"
              />
              <label htmlFor="baseline-upload" className="cursor-pointer">
                {baseline ? (
                  <div className="flex flex-col items-center">
                    <Upload className="h-10 w-10 text-green-500 mb-3" />
                    <p className="font-medium text-green-700">{baseline.name}</p>
                    <p className="text-sm text-gray-500 mt-1">
                      {(baseline.size / 1024).toFixed(1)} KB
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

        {/* Production Snapshot */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Production Snapshot</CardTitle>
          </CardHeader>
          <CardContent>
            <div
              onDrop={handleDrop(setSnapshot, false)}
              onDragOver={handleDragOver}
              className={`
                border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
                ${snapshot ? 'border-green-400 bg-green-50' : 'border-gray-300 hover:border-purple-400 hover:bg-purple-50'}
              `}
            >
              <input
                type="file"
                accept={acceptedExtensions}
                onChange={handleFileChange(setSnapshot, false)}
                className="hidden"
                id="snapshot-upload"
              />
              <label htmlFor="snapshot-upload" className="cursor-pointer">
                {snapshot ? (
                  <div className="flex flex-col items-center">
                    <Upload className="h-10 w-10 text-green-500 mb-3" />
                    <p className="font-medium text-green-700">{snapshot.name}</p>
                    <p className="text-sm text-gray-500 mt-1">
                      {(snapshot.size / 1024).toFixed(1)} KB
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

      {/* Target Column Selector (Optional - for Concept Drift) */}
      {baseline && snapshot && (
        <Card className="mb-6 border-indigo-200">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Brain className="h-5 w-5 text-indigo-600" />
              Concept Drift Detection (Optional)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-600 mb-3">
              Select a target column to detect concept drift -- changes in the relationship between features and the target variable (P(Y|X)).
              This runs prediction-based analysis, feature importance comparison, and conditional distribution checks.
            </p>
            <div className="flex items-center gap-4">
              <label htmlFor="target-column" className="text-sm font-medium text-gray-700 whitespace-nowrap">
                Target Column:
              </label>
              <select
                id="target-column"
                value={targetColumn}
                onChange={(e) => setTargetColumn(e.target.value)}
                disabled={loadingColumns || columns.length === 0}
                className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm
                           focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="">None (feature drift only)</option>
                {columns.map((col) => (
                  <option key={col.name} value={col.name}>
                    {col.name} ({col.type})
                  </option>
                ))}
              </select>
              {loadingColumns && <Loader2 className="h-4 w-4 animate-spin text-indigo-500" />}
            </div>
            {targetColumn && (
              <p className="text-xs text-indigo-600 mt-2">
                Concept drift analysis will run using "{targetColumn}" as the target variable.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Detect Drift Button */}
      <div className="flex justify-center mb-8">
        <Button
          onClick={handleDetectDrift}
          size="lg"
          disabled={!baseline || !snapshot || loading}
          className="px-12"
        >
          {loading ? (
            <>
              <Loader2 className="h-5 w-5 mr-2 animate-spin" />
              {targetColumn ? 'Detecting Feature & Concept Drift...' : 'Detecting Drift...'}
            </>
          ) : (
            <>
              <Activity className="h-5 w-5 mr-2" />
              {targetColumn ? 'Detect Feature & Concept Drift' : 'Detect Drift'}
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
          {/* Feature Drift Section Header */}
          <div className="flex items-center gap-3">
            <Activity className="h-7 w-7 text-purple-600" />
            <h2 className="text-2xl font-bold">Feature Drift Analysis</h2>
          </div>

          {/* Overall Drift Score */}
          <Card>
            <CardContent className="p-6">
              <div className="text-center">
                <p className="text-sm font-medium text-gray-600 mb-2">Overall Feature Drift Score</p>
                <div className={`text-6xl font-bold mb-3 ${getDriftScoreColor(results.overall_drift_score)}`}>
                  {Math.round(results.overall_drift_score * 100)}%
                </div>
                <div className="w-full max-w-md mx-auto bg-gray-200 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full transition-all ${getDriftBarColor(results.overall_drift_score)}`}
                    style={{ width: `${Math.round(results.overall_drift_score * 100)}%` }}
                  />
                </div>
                <p className="text-sm text-gray-500 mt-3">
                  {results.overall_drift_score <= 0.2
                    ? 'Minimal drift detected -- distributions are stable.'
                    : results.overall_drift_score <= 0.5
                    ? 'Moderate drift detected -- some columns have shifted.'
                    : 'Significant drift detected -- immediate investigation recommended.'}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Alert Counts Summary */}
          <div className="grid grid-cols-3 gap-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-5 w-5 text-green-500" />
                    <span className="text-sm font-medium text-gray-700">Stable</span>
                  </div>
                  <span className="text-2xl font-bold text-green-600">{results.alert_counts.green}</span>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5 text-yellow-500" />
                    <span className="text-sm font-medium text-gray-700">Warning</span>
                  </div>
                  <span className="text-2xl font-bold text-yellow-600">{results.alert_counts.yellow}</span>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-red-500">
                      <span className="h-2.5 w-2.5 rounded-full bg-white" />
                    </span>
                    <span className="text-sm font-medium text-gray-700">Critical</span>
                  </div>
                  <span className="text-2xl font-bold text-red-600">{results.alert_counts.red}</span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Per-Column Drift Table */}
          {results.columns && results.columns.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Per-Column Drift Analysis</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b-2 border-gray-300">
                        <th className="text-left py-3 px-4">Column Name</th>
                        <th className="text-left py-3 px-4">Type</th>
                        <th className="text-right py-3 px-4">Drift Score</th>
                        <th className="text-right py-3 px-4">P-Value</th>
                        <th className="text-left py-3 px-4">Test Used</th>
                        <th className="text-center py-3 px-4">Alert Level</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.columns.map((col: ColumnDriftResult) => (
                        <tr key={col.column_name} className="border-b border-gray-200 hover:bg-gray-50">
                          <td className="py-3 px-4 font-medium">{col.column_name}</td>
                          <td className="py-3 px-4">
                            <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${
                              col.column_type === 'numeric'
                                ? 'bg-blue-100 text-blue-800'
                                : 'bg-purple-100 text-purple-800'
                            }`}>
                              {col.column_type}
                            </span>
                          </td>
                          <td className="text-right py-3 px-4">
                            <span className={`font-semibold ${getDriftScoreColor(col.drift_score)}`}>
                              {(col.drift_score * 100).toFixed(1)}%
                            </span>
                          </td>
                          <td className="text-right py-3 px-4 text-gray-600">
                            {col.p_value.toFixed(4)}
                          </td>
                          <td className="py-3 px-4 text-gray-600">{col.test_used}</td>
                          <td className="py-3 px-4">
                            <div className="flex items-center justify-center gap-2">
                              {getAlertIcon(col.alert_level)}
                              <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${getAlertBadgeClasses(col.alert_level)}`}>
                                {col.alert_level.charAt(0).toUpperCase() + col.alert_level.slice(1)}
                              </span>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Feature Drift Summary Text */}
          {results.summary && (
            <Card>
              <CardHeader>
                <CardTitle>Feature Drift Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-gray-50 rounded-lg p-4">
                  <pre className="whitespace-pre-wrap text-sm text-gray-700 font-sans leading-relaxed">
                    {results.summary}
                  </pre>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Concept Drift Section */}
          {results.concept_drift && renderConceptDrift(results.concept_drift)}
        </div>
      )}
    </div>
  );
}
