import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Download, BarChart3, CheckCircle, Shield, Sparkles, TrendingUp, FileText, Activity, ChevronDown, ChevronUp, FileDown } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/Card';
import { Button } from '../components/Button';
import { getJobStatus, getValidation, downloadSyntheticBlob } from '../services/api';
import { JobStatus } from '../types';
import {
  BarChart,
  Bar,
  AreaChart,
  Area,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';

// Import external components
import PrivacyOverview from '../components/PrivacyOverview';
import NovelQualityMetricsComponent from '../components/NovelQualityMetrics';
import TimeSeriesMetrics from '../components/TimeSeriesMetrics';
import CorrelationHeatmap from '../components/CorrelationHeatmap';
import ErrorBanner from '../components/ErrorBanner';
import { getApiErrorMessage } from '../lib/utils';

export default function Results() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [validation, setValidation] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedColumn, setSelectedColumn] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'overview' | 'distributions' | 'relationships' | 'details'>('overview');
  const [structuralDetailsExpanded, setStructuralDetailsExpanded] = useState(false);
  const [generatingPdf, setGeneratingPdf] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!jobId) return;

      try {
        const statusData = await getJobStatus(jobId);
        if (statusData.status !== JobStatus.COMPLETED) {
          navigate(`/generate/${jobId}`);
          return;
        }

        const validationData = await getValidation(jobId);
        setValidation(validationData);

        // Set default selected column
        if (validationData.metrics.column_metrics) {
          const columns = Object.keys(validationData.metrics.column_metrics);
          if (columns.length > 0) {
            setSelectedColumn(columns[0]);
          }
        }
      } catch (err: unknown) {
        setError(getApiErrorMessage(err));
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [jobId, navigate]);

  const handleDownload = async () => {
    try {
      const blob = await downloadSyntheticBlob(jobId!);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `synthetic_data_${jobId}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: unknown) {
      console.error('Download error:', err);
      setActionError(getApiErrorMessage(err));
    }
  };

  const handleExportPDF = async () => {
    if (!validation || !jobId) return;
    setGeneratingPdf(true);
    try {
      const { generateValidationReport } = await import('../utils/reportGenerator');
      await generateValidationReport(validation, jobId);
    } catch (err: unknown) {
      console.error('PDF export error:', err);
      setActionError('Failed to generate PDF report. Make sure jspdf and html2canvas are installed.');
    } finally {
      setGeneratingPdf(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="flex items-center justify-center h-64">
          <div className="text-lg text-gray-600">Loading validation metrics...</div>
        </div>
      </div>
    );
  }

  if (error || !validation) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <Card>
          <CardContent className="p-8 text-center">
            <p className="text-red-600">{error || 'No validation data available'}</p>
            <Button onClick={() => navigate('/')} className="mt-4">
              Go Home
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const metrics = validation.metrics;

  // Calculate key percentages
  const qualityPercent = Math.round(metrics.quality_score * 100);
  const correlationPercent = Math.round(metrics.statistical_similarity.correlation_preservation * 100);
  const privacyPercent = Math.round(metrics.privacy_score * 100);
  const novelScore = metrics.novel_quality_metrics
    ? Math.round(metrics.novel_quality_metrics.overall_novel_quality_score * 100)
    : 0;

  // Prepare chart data
  const divergenceData = Object.entries(metrics.column_metrics).map(([col, m]: [string, any]) => ({
    column: col,
    'JS Divergence': m.js_divergence ? (m.js_divergence * 100).toFixed(2) : 0,
    'Overlap': m.distribution_overlap ? (m.distribution_overlap * 100).toFixed(2) : 0
  }));

  const columnQualityData = Object.entries(metrics.column_metrics).map(([col, m]: [string, any]) => ({
    column: col,
    quality: m.quality_score ? (m.quality_score * 100).toFixed(1) : 0
  }));

  const measuresData = Object.entries(metrics.column_metrics)
    .filter(([_, m]: [string, any]) => m.original_mean !== undefined)
    .map(([col, m]: [string, any]) => ({
      column: col,
      'Original Mean': m.original_mean?.toFixed(3) || 'N/A',
      'Synthetic Mean': m.synthetic_mean?.toFixed(3) || 'N/A',
      'Original Std': m.original_std?.toFixed(3) || 'N/A',
      'Synthetic Std': m.synthetic_std?.toFixed(3) || 'N/A'
    }));

  const numericTests = metrics.relationship_tests?.numeric_pairs || [];
  const categoricalTests = metrics.relationship_tests?.categorical_pairs || [];

  const selectedMetrics = selectedColumn ? metrics.column_metrics[selectedColumn] : null;

  const getDistributionOverlapData = (columnMetrics: any) => {
    if (columnMetrics.histogram_data) {
      const bins = columnMetrics.histogram_data.bins;
      const origCounts = columnMetrics.histogram_data.original;
      const synthCounts = columnMetrics.histogram_data.synthetic;

      return bins.slice(0, -1).map((bin: number, idx: number) => ({
        bin: bin.toFixed(2),
        original: (origCounts[idx] * 100).toFixed(2),
        synthetic: (synthCounts[idx] * 100).toFixed(2)
      }));
    } else if (columnMetrics.category_data) {
      const categories = columnMetrics.category_data.categories;
      const origCounts = columnMetrics.category_data.original;
      const synthCounts = columnMetrics.category_data.synthetic;

      return categories.map((cat: string, idx: number) => ({
        category: cat,
        original: (origCounts[idx] * 100).toFixed(2),
        synthetic: (synthCounts[idx] * 100).toFixed(2)
      }));
    }
    return [];
  };

  // Tab content components
  const OverviewTab = () => (
    <div className="space-y-6">
      {/* Quality Score Hero - Compact */}
      <div className="flex items-center justify-center p-6 bg-gradient-to-br from-blue-500 to-blue-700 rounded-xl">
        <div className="text-center text-white">
          <div className="text-5xl font-bold mb-1">{qualityPercent}%</div>
          <div className="text-lg opacity-90">Overall Quality Score</div>
        </div>
      </div>

      {/* Key Metrics - Compact Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 bg-white border border-gray-200 rounded-lg">
          <div className="flex items-center mb-2">
            <BarChart3 className="h-4 w-4 mr-2 text-blue-600" />
            <div className="text-sm font-medium text-gray-600">Fidelity</div>
          </div>
          <div className="text-2xl font-bold text-blue-600">{qualityPercent}%</div>
          <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2">
            <div className="bg-blue-600 h-1.5 rounded-full" style={{ width: `${qualityPercent}%` }} />
          </div>
        </div>

        <div className="p-4 bg-white border border-gray-200 rounded-lg">
          <div className="flex items-center mb-2">
            <CheckCircle className="h-4 w-4 mr-2 text-green-600" />
            <div className="text-sm font-medium text-gray-600">Correlation</div>
          </div>
          <div className="text-2xl font-bold text-green-600">{correlationPercent}%</div>
          <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2">
            <div className="bg-green-600 h-1.5 rounded-full" style={{ width: `${correlationPercent}%` }} />
          </div>
        </div>

        <div className="p-4 bg-white border border-gray-200 rounded-lg">
          <div className="flex items-center mb-2">
            <Shield className="h-4 w-4 mr-2 text-purple-600" />
            <div className="text-sm font-medium text-gray-600">Privacy</div>
          </div>
          <div className="text-2xl font-bold text-purple-600">{privacyPercent}%</div>
          <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2">
            <div className="bg-purple-600 h-1.5 rounded-full" style={{ width: `${privacyPercent}%` }} />
          </div>
        </div>

        {metrics.novel_quality_metrics && (
          <div className="p-4 bg-gradient-to-br from-emerald-50 to-teal-50 border-2 border-emerald-200 rounded-lg">
            <div className="flex items-center mb-2">
              <Sparkles className="h-4 w-4 mr-2 text-emerald-600" />
              <div className="text-sm font-medium text-emerald-700">ML Efficacy</div>
            </div>
            <div className="text-2xl font-bold text-emerald-600">{novelScore}%</div>
            <div className="w-full bg-emerald-200 rounded-full h-1.5 mt-2">
              <div className="bg-gradient-to-r from-emerald-500 to-teal-500 h-1.5 rounded-full" style={{ width: `${novelScore}%` }} />
            </div>
          </div>
        )}
      </div>

      {/* Privacy Overview */}
      <PrivacyOverview
        privacyMetrics={metrics.privacy_metrics || {}}
        privacyScore={metrics.privacy_score}
      />

      {/* Novel Quality Metrics */}
      {metrics.novel_quality_metrics && (
        <NovelQualityMetricsComponent novelMetrics={metrics.novel_quality_metrics} />
      )}

      {/* Time-Series ML Efficacy */}
      {metrics.novel_quality_metrics?.time_series_ml_efficacy && (
        <TimeSeriesMetrics tsMetrics={metrics.novel_quality_metrics.time_series_ml_efficacy} />
      )}

      {/* Structural Similarity - Compact */}
      {metrics.structural_similarity && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <Activity className="h-5 w-5 mr-2 text-indigo-600" />
                <CardTitle>Structural Similarity</CardTitle>
              </div>
              <span className="text-3xl font-bold text-indigo-600">
                {Math.round(metrics.structural_similarity.overall_structural_score * 100)}%
              </span>
            </div>
          </CardHeader>
          <CardContent>
            {/* Compact Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <div className="text-center p-3 bg-blue-50 rounded">
                <div className="text-xs text-gray-600 mb-1">Schema</div>
                <div className="text-lg font-bold text-blue-600">
                  {Math.round(metrics.structural_similarity.summary.schema_score * 100)}%
                </div>
              </div>
              <div className="text-center p-3 bg-green-50 rounded">
                <div className="text-xs text-gray-600 mb-1">Missing Pattern</div>
                <div className="text-lg font-bold text-green-600">
                  {Math.round(metrics.structural_similarity.summary.missing_pattern_score * 100)}%
                </div>
              </div>
              <div className="text-center p-3 bg-purple-50 rounded">
                <div className="text-xs text-gray-600 mb-1">Value Ranges</div>
                <div className="text-lg font-bold text-purple-600">
                  {Math.round(metrics.structural_similarity.summary.value_range_score * 100)}%
                </div>
              </div>
              <div className="text-center p-3 bg-orange-50 rounded">
                <div className="text-xs text-gray-600 mb-1">Cardinality</div>
                <div className="text-lg font-bold text-orange-600">
                  {Math.round(metrics.structural_similarity.summary.cardinality_score * 100)}%
                </div>
              </div>
              <div className="text-center p-3 bg-teal-50 rounded">
                <div className="text-xs text-gray-600 mb-1">Data Quality</div>
                <div className="text-lg font-bold text-teal-600">
                  {Math.round(metrics.structural_similarity.summary.data_quality_score * 100)}%
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Statistical Summary - Compact */}
      <Card>
        <CardHeader>
          <CardTitle>Statistical Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-600 mb-1">Avg Column Quality</p>
              <p className="text-xl font-bold">
                {Math.round(metrics.statistical_similarity.avg_column_quality * 100)}%
              </p>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-600 mb-1">Correlation Preservation</p>
              <p className="text-xl font-bold">
                {Math.round(metrics.statistical_similarity.correlation_preservation * 100)}%
              </p>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-600 mb-1">Columns Evaluated</p>
              <p className="text-xl font-bold">
                {metrics.statistical_similarity.num_columns_evaluated}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );

  const DistributionsTab = () => (
    <div className="space-y-6">
      {/* Distribution Divergence Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Distribution Divergence</CardTitle>
          <CardDescription>Jensen-Shannon divergence and overlap across all features</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={divergenceData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="column" angle={-45} textAnchor="end" height={80} fontSize={10} />
              <YAxis label={{ value: 'Divergence (%)', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend />
              <Bar dataKey="JS Divergence" fill="#3b82f6" />
              <Bar dataKey="Overlap" fill="#10b981" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Distribution Overlap with Column Selector */}
      <Card>
        <CardHeader>
          <CardTitle>Distribution Overlap</CardTitle>
          <CardDescription>Compare original vs synthetic distributions by feature</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Column:
            </label>
            <select
              className="w-full md:w-1/2 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={selectedColumn || ''}
              onChange={(e) => setSelectedColumn(e.target.value)}
            >
              {Object.keys(metrics.column_metrics).map((col) => (
                <option key={col} value={col}>
                  {col}
                </option>
              ))}
            </select>
          </div>

          {selectedMetrics && (
            <div>
              {/* Compact Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                {selectedMetrics.js_divergence !== undefined && (
                  <div className="bg-blue-50 p-3 rounded-lg">
                    <p className="text-xs text-gray-600">JS Divergence</p>
                    <p className="text-lg font-bold text-blue-600">
                      {selectedMetrics.js_divergence.toFixed(4)}
                    </p>
                  </div>
                )}
                {selectedMetrics.kl_divergence !== undefined && (
                  <div className="bg-purple-50 p-3 rounded-lg">
                    <p className="text-xs text-gray-600">KL Divergence</p>
                    <p className="text-lg font-bold text-purple-600">
                      {selectedMetrics.kl_divergence.toFixed(4)}
                    </p>
                  </div>
                )}
                {selectedMetrics.distribution_overlap !== undefined && (
                  <div className="bg-green-50 p-3 rounded-lg">
                    <p className="text-xs text-gray-600">Distribution Overlap</p>
                    <p className="text-lg font-bold text-green-600">
                      {(selectedMetrics.distribution_overlap * 100).toFixed(1)}%
                    </p>
                  </div>
                )}
                {selectedMetrics.ks_pvalue !== undefined && (
                  <div className="bg-orange-50 p-3 rounded-lg">
                    <p className="text-xs text-gray-600">KS Test p-value</p>
                    <p className="text-lg font-bold text-orange-600">
                      {selectedMetrics.ks_pvalue.toFixed(4)}
                    </p>
                  </div>
                )}
              </div>

              {/* Chart */}
              <ResponsiveContainer width="100%" height={280}>
                {selectedMetrics.histogram_data ? (
                  <AreaChart data={getDistributionOverlapData(selectedMetrics)}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="bin" fontSize={10} />
                    <YAxis label={{ value: 'Density (%)', angle: -90, position: 'insideLeft' }} />
                    <Tooltip />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="original"
                      stroke="#3b82f6"
                      fill="#3b82f6"
                      fillOpacity={0.3}
                      name="Original"
                    />
                    <Area
                      type="monotone"
                      dataKey="synthetic"
                      stroke="#10b981"
                      fill="#10b981"
                      fillOpacity={0.3}
                      name="Synthetic"
                    />
                  </AreaChart>
                ) : (
                  <BarChart data={getDistributionOverlapData(selectedMetrics)}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="category" angle={-45} textAnchor="end" height={80} fontSize={10} />
                    <YAxis label={{ value: 'Frequency (%)', angle: -90, position: 'insideLeft' }} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="original" fill="#3b82f6" name="Original" />
                    <Bar dataKey="synthetic" fill="#10b981" name="Synthetic" />
                  </BarChart>
                )}
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Column Quality Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Column Quality Scores</CardTitle>
          <CardDescription>Quality score per feature</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={columnQualityData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="column" angle={-45} textAnchor="end" height={80} fontSize={10} />
              <YAxis domain={[0, 100]} />
              <Tooltip />
              <Legend />
              <Bar dataKey="quality" fill="#3b82f6" name="Quality Score (%)" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );

  // Scatter plot data for mean and std comparisons
  const meanScatterData = Object.entries(metrics.column_metrics)
    .filter(([_, m]: [string, any]) => m.original_mean !== undefined && m.synthetic_mean !== undefined)
    .map(([col, m]: [string, any]) => ({
      name: col,
      original: m.original_mean,
      synthetic: m.synthetic_mean,
    }));

  const stdScatterData = Object.entries(metrics.column_metrics)
    .filter(([_, m]: [string, any]) => m.original_std !== undefined && m.synthetic_std !== undefined)
    .map(([col, m]: [string, any]) => ({
      name: col,
      original: m.original_std,
      synthetic: m.synthetic_std,
    }));

  const correlationMatrices = validation.charts?.correlation_matrices;

  const RelationshipsTab = () => (
    <div className="space-y-6">
      {/* Correlation Heatmap */}
      {correlationMatrices?.original && correlationMatrices?.synthetic && (
        <CorrelationHeatmap
          original={correlationMatrices.original}
          synthetic={correlationMatrices.synthetic}
        />
      )}

      {/* Mean & Std Scatter Plots */}
      {meanScatterData.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Mean Comparison Scatter */}
          <Card>
            <CardHeader>
              <CardTitle>Mean Comparison</CardTitle>
              <CardDescription>Original vs Synthetic mean per column (diagonal = perfect)</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    type="number"
                    dataKey="original"
                    name="Original Mean"
                    label={{ value: 'Original', position: 'bottom', offset: 0 }}
                  />
                  <YAxis
                    type="number"
                    dataKey="synthetic"
                    name="Synthetic Mean"
                    label={{ value: 'Synthetic', angle: -90, position: 'insideLeft' }}
                  />
                  <Tooltip
                    formatter={(value: number) => value.toFixed(4)}
                    labelFormatter={(_: any, payload: readonly any[]) => payload?.[0]?.payload?.name || ''}
                  />
                  <ReferenceLine
                    segment={[
                      { x: Math.min(...meanScatterData.map(d => Math.min(d.original, d.synthetic))),
                        y: Math.min(...meanScatterData.map(d => Math.min(d.original, d.synthetic))) },
                      { x: Math.max(...meanScatterData.map(d => Math.max(d.original, d.synthetic))),
                        y: Math.max(...meanScatterData.map(d => Math.max(d.original, d.synthetic))) }
                    ]}
                    stroke="#9ca3af"
                    strokeDasharray="5 5"
                  />
                  <Scatter data={meanScatterData} fill="#3b82f6" />
                </ScatterChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Std Dev Comparison Scatter */}
          <Card>
            <CardHeader>
              <CardTitle>Std Dev Comparison</CardTitle>
              <CardDescription>Original vs Synthetic std dev per column (diagonal = perfect)</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    type="number"
                    dataKey="original"
                    name="Original Std"
                    label={{ value: 'Original', position: 'bottom', offset: 0 }}
                  />
                  <YAxis
                    type="number"
                    dataKey="synthetic"
                    name="Synthetic Std"
                    label={{ value: 'Synthetic', angle: -90, position: 'insideLeft' }}
                  />
                  <Tooltip
                    formatter={(value: number) => value.toFixed(4)}
                    labelFormatter={(_: any, payload: readonly any[]) => payload?.[0]?.payload?.name || ''}
                  />
                  <ReferenceLine
                    segment={[
                      { x: Math.min(...stdScatterData.map(d => Math.min(d.original, d.synthetic))),
                        y: Math.min(...stdScatterData.map(d => Math.min(d.original, d.synthetic))) },
                      { x: Math.max(...stdScatterData.map(d => Math.max(d.original, d.synthetic))),
                        y: Math.max(...stdScatterData.map(d => Math.max(d.original, d.synthetic))) }
                    ]}
                    stroke="#9ca3af"
                    strokeDasharray="5 5"
                  />
                  <Scatter data={stdScatterData} fill="#10b981" />
                </ScatterChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Statistical Measures Table */}
      {measuresData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Statistical Measures</CardTitle>
            <CardDescription>Mean and standard deviation comparison</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b-2 border-gray-300">
                    <th className="text-left py-2 px-3">Column</th>
                    <th className="text-right py-2 px-3">Orig. Mean</th>
                    <th className="text-right py-2 px-3">Synth. Mean</th>
                    <th className="text-right py-2 px-3">Orig. Std</th>
                    <th className="text-right py-2 px-3">Synth. Std</th>
                  </tr>
                </thead>
                <tbody>
                  {measuresData.map((row, idx) => (
                    <tr key={idx} className="border-b border-gray-200 hover:bg-gray-50">
                      <td className="py-2 px-3 font-medium">{row.column}</td>
                      <td className="text-right py-2 px-3">{row['Original Mean']}</td>
                      <td className="text-right py-2 px-3">{row['Synthetic Mean']}</td>
                      <td className="text-right py-2 px-3">{row['Original Std']}</td>
                      <td className="text-right py-2 px-3">{row['Synthetic Std']}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Relationship Tests */}
      {(numericTests.length > 0 || categoricalTests.length > 0) && (
        <Card>
          <CardHeader>
            <div className="flex items-center">
              <TrendingUp className="h-5 w-5 mr-2" />
              <CardTitle>Relationship Tests</CardTitle>
            </div>
            <CardDescription>Statistical tests for feature relationships</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {numericTests.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-3">Numeric Feature Pairs (T-tests)</h3>
                <div className="overflow-x-auto max-h-96 overflow-y-auto border border-gray-200 rounded-lg">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 sticky top-0">
                      <tr className="border-b-2 border-gray-300">
                        <th className="text-left py-2 px-2">Feature 1</th>
                        <th className="text-left py-2 px-2">Feature 2</th>
                        <th className="text-center py-2 px-2">Orig. p-value</th>
                        <th className="text-center py-2 px-2">Synth. p-value</th>
                        <th className="text-center py-2 px-2">Hypothesis Match</th>
                      </tr>
                    </thead>
                    <tbody>
                      {numericTests.map((test: any, idx: number) => (
                        <tr key={idx} className="border-b border-gray-200 hover:bg-gray-50">
                          <td className="py-2 px-2">{test.feature_1}</td>
                          <td className="py-2 px-2">{test.feature_2}</td>
                          <td className="text-center py-2 px-2">{test.original_pvalue.toFixed(4)}</td>
                          <td className="text-center py-2 px-2">{test.synthetic_pvalue.toFixed(4)}</td>
                          <td className="text-center py-2 px-2">
                            <span
                              className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${
                                test.hypothesis_consistent
                                  ? 'bg-green-100 text-green-800'
                                  : 'bg-red-100 text-red-800'
                              }`}
                            >
                              {test.hypothesis_consistent ? '✓ Match' : '✗ Mismatch'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="text-sm text-gray-500 mt-2">
                  Showing all {numericTests.length} tests
                </p>
              </div>
            )}

            {categoricalTests.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-3">Categorical Feature Pairs (Chi-Square Tests)</h3>
                <div className="overflow-x-auto max-h-96 overflow-y-auto border border-gray-200 rounded-lg">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 sticky top-0">
                      <tr className="border-b-2 border-gray-300">
                        <th className="text-left py-2 px-2">Feature 1</th>
                        <th className="text-left py-2 px-2">Feature 2</th>
                        <th className="text-center py-2 px-2">Orig. p-value</th>
                        <th className="text-center py-2 px-2">Synth. p-value</th>
                        <th className="text-center py-2 px-2">Hypothesis Match</th>
                      </tr>
                    </thead>
                    <tbody>
                      {categoricalTests.map((test: any, idx: number) => (
                        <tr key={idx} className="border-b border-gray-200 hover:bg-gray-50">
                          <td className="py-2 px-2">{test.feature_1}</td>
                          <td className="py-2 px-2">{test.feature_2}</td>
                          <td className="text-center py-2 px-2">{test.original_pvalue.toFixed(4)}</td>
                          <td className="text-center py-2 px-2">{test.synthetic_pvalue.toFixed(4)}</td>
                          <td className="text-center py-2 px-2">
                            <span
                              className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${
                                test.hypothesis_consistent
                                  ? 'bg-green-100 text-green-800'
                                  : 'bg-red-100 text-red-800'
                              }`}
                            >
                              {test.hypothesis_consistent ? '✓ Match' : '✗ Mismatch'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="text-sm text-gray-500 mt-2">
                  Showing all {categoricalTests.length} tests
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );

  const DetailsTab = () => (
    <div className="space-y-6">
      {/* Detailed Assessment Summary */}
      <Card>
        <CardHeader>
          <div className="flex items-center">
            <FileText className="h-5 w-5 mr-2 text-blue-600" />
            <CardTitle>Detailed Assessment Summary</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {(() => {
            const lines = validation.assessment_summary.split('\n');
            const sections: { title: string; content: string[] }[] = [];
            let currentSection: { title: string; content: string[] } | null = null;

            lines.forEach((line: string) => {
              const trimmedLine = line.trim();
              if (trimmedLine.startsWith('===') && trimmedLine.endsWith('===')) {
                if (currentSection) sections.push(currentSection);
                const title = trimmedLine.replace(/===/g, '').trim();
                currentSection = { title, content: [] };
              } else if (trimmedLine && currentSection) {
                currentSection.content.push(trimmedLine);
              }
            });
            if (currentSection) sections.push(currentSection);

            return (
              <div className="space-y-6">
                {sections.map((section, idx) => (
                  <div key={idx} className="border-l-4 border-blue-500 pl-4 py-2">
                    <h3 className="text-lg font-bold text-gray-900 mb-3">{section.title}</h3>
                    <div className="space-y-2">
                      {section.content.map((line, lineIdx) => {
                        if (line.includes(':')) {
                          const [label, ...valueParts] = line.split(':');
                          const value = valueParts.join(':').trim();

                          return (
                            <div key={lineIdx} className="flex flex-col sm:flex-row sm:gap-2">
                              <span className="font-semibold text-gray-700 min-w-fit">{label}:</span>
                              <span className="text-gray-600">{value}</span>
                            </div>
                          );
                        }
                        return (
                          <p key={lineIdx} className="text-gray-600 leading-relaxed">
                            {line}
                          </p>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            );
          })()}
        </CardContent>
      </Card>

      {/* Structural Similarity - Detailed */}
      {metrics.structural_similarity && (
        <Card>
          <CardHeader
            className="cursor-pointer hover:bg-gray-50 transition-colors"
            onClick={() => setStructuralDetailsExpanded(!structuralDetailsExpanded)}
          >
            <div className="flex items-center justify-between">
              <CardTitle>Structural Similarity Details</CardTitle>
              <button className="p-1 hover:bg-gray-200 rounded-full transition-colors">
                {structuralDetailsExpanded ? (
                  <ChevronUp className="h-5 w-5 text-gray-600" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-600" />
                )}
              </button>
            </div>
          </CardHeader>
          {structuralDetailsExpanded && (
          <CardContent className="space-y-6">
            {/* Schema Validation */}
            <div className="border-l-4 border-blue-500 pl-4 py-2">
              <h4 className="font-semibold text-gray-900 mb-2">Schema Validation</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Columns: </span>
                  <span className="font-medium">
                    {metrics.structural_similarity.schema_validation.column_count_match ? (
                      <span className="text-green-600">✓ Match</span>
                    ) : (
                      <span className="text-yellow-600">
                        {metrics.structural_similarity.schema_validation.original_column_count} → {metrics.structural_similarity.schema_validation.synthetic_column_count}
                      </span>
                    )}
                  </span>
                </div>
                <div>
                  <span className="text-gray-600">Names: </span>
                  <span className="font-medium">
                    {metrics.structural_similarity.schema_validation.column_names_match ? (
                      <span className="text-green-600">✓ Match</span>
                    ) : (
                      <span className="text-yellow-600">Partial</span>
                    )}
                  </span>
                </div>
                <div>
                  <span className="text-gray-600">Data Types: </span>
                  <span className="font-medium text-blue-600">
                    {Math.round(metrics.structural_similarity.schema_validation.type_match_score * 100)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Data Quality */}
            <div className="border-l-4 border-teal-500 pl-4 py-2">
              <h4 className="font-semibold text-gray-900 mb-2">Data Quality</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Original Nulls: </span>
                  <span className="font-medium">
                    {metrics.structural_similarity.data_quality.overall_null_rate_original.toFixed(2)}%
                  </span>
                </div>
                <div>
                  <span className="text-gray-600">Synthetic Nulls: </span>
                  <span className="font-medium">
                    {metrics.structural_similarity.data_quality.overall_null_rate_synthetic.toFixed(2)}%
                  </span>
                </div>
                <div>
                  <span className="text-gray-600">Row Count: </span>
                  <span className="font-medium">
                    {metrics.structural_similarity.data_quality.row_count_synthetic.toLocaleString()}
                  </span>
                </div>
              </div>
            </div>

            {/* Value Ranges */}
            {Object.keys(metrics.structural_similarity.value_ranges.numeric_columns).length > 0 && (
              <div className="border-l-4 border-purple-500 pl-4 py-2">
                <h4 className="font-semibold text-gray-900 mb-3">Value Range Preservation</h4>
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-3 py-2 text-left font-medium text-gray-700">Column</th>
                        <th className="px-3 py-2 text-left font-medium text-gray-700">Original Range</th>
                        <th className="px-3 py-2 text-left font-medium text-gray-700">Synthetic Range</th>
                        <th className="px-3 py-2 text-left font-medium text-gray-700">Within Bounds</th>
                        <th className="px-3 py-2 text-left font-medium text-gray-700">Score</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {Object.entries(metrics.structural_similarity.value_ranges.numeric_columns).slice(0, 10).map(([col, data]: [string, any]) => (
                        <tr key={col}>
                          <td className="px-3 py-2 font-medium text-gray-900">{col}</td>
                          <td className="px-3 py-2 text-gray-600">
                            [{data.original_min.toFixed(2)}, {data.original_max.toFixed(2)}]
                          </td>
                          <td className="px-3 py-2 text-gray-600">
                            [{data.synthetic_min.toFixed(2)}, {data.synthetic_max.toFixed(2)}]
                          </td>
                          <td className="px-3 py-2">
                            {data.within_bounds ? (
                              <span className="text-green-600 font-medium">✓ Yes</span>
                            ) : (
                              <span className="text-yellow-600 font-medium">⚠ No</span>
                            )}
                          </td>
                          <td className="px-3 py-2">
                            <span className={`font-medium ${data.range_preservation_score >= 0.8 ? 'text-green-600' : data.range_preservation_score >= 0.6 ? 'text-yellow-600' : 'text-red-600'}`}>
                              {Math.round(data.range_preservation_score * 100)}%
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Cardinality */}
            {Object.keys(metrics.structural_similarity.cardinality.categorical_columns).length > 0 && (
              <div className="border-l-4 border-orange-500 pl-4 py-2">
                <h4 className="font-semibold text-gray-900 mb-3">Cardinality Preservation</h4>
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-3 py-2 text-left font-medium text-gray-700">Column</th>
                        <th className="px-3 py-2 text-left font-medium text-gray-700">Original Unique</th>
                        <th className="px-3 py-2 text-left font-medium text-gray-700">Synthetic Unique</th>
                        <th className="px-3 py-2 text-left font-medium text-gray-700">Category Preservation</th>
                        <th className="px-3 py-2 text-left font-medium text-gray-700">Score</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {Object.entries(metrics.structural_similarity.cardinality.categorical_columns).slice(0, 10).map(([col, data]: [string, any]) => (
                        <tr key={col}>
                          <td className="px-3 py-2 font-medium text-gray-900">{col}</td>
                          <td className="px-3 py-2 text-gray-600">{data.original_unique_count}</td>
                          <td className="px-3 py-2 text-gray-600">{data.synthetic_unique_count}</td>
                          <td className="px-3 py-2 text-gray-600">
                            {Math.round(data.category_preservation_rate * 100)}%
                          </td>
                          <td className="px-3 py-2">
                            <span className={`font-medium ${data.similarity_score >= 0.8 ? 'text-green-600' : data.similarity_score >= 0.6 ? 'text-yellow-600' : 'text-red-600'}`}>
                              {Math.round(data.similarity_score * 100)}%
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </CardContent>
          )}
        </Card>
      )}
    </div>
  );

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {actionError && <ErrorBanner message={actionError} onDismiss={() => setActionError(null)} />}
      {/* Header with Download Button */}
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold mb-1">Results Dashboard</h1>
          <p className="text-gray-600">Synthetic data quality and validation metrics</p>
        </div>
        <div className="flex gap-3">
          <Button onClick={handleExportPDF} variant="outline" disabled={generatingPdf}>
            <FileDown className="h-4 w-4 mr-2" />
            {generatingPdf ? 'Generating...' : 'PDF Report'}
          </Button>
          <Button onClick={handleDownload} size="lg">
            <Download className="h-4 w-4 mr-2" />
            Download
          </Button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="mb-6 border-b border-gray-200">
        <nav className="flex space-x-6">
          <button
            onClick={() => setActiveTab('overview')}
            className={`pb-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'overview'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('distributions')}
            className={`pb-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'distributions'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Distributions
          </button>
          <button
            onClick={() => setActiveTab('relationships')}
            className={`pb-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'relationships'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Relationships
          </button>
          <button
            onClick={() => setActiveTab('details')}
            className={`pb-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'details'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Details
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      <div id="results-dashboard">
      {activeTab === 'overview' && <OverviewTab />}
      {activeTab === 'distributions' && <DistributionsTab />}
      {activeTab === 'relationships' && <RelationshipsTab />}
      {activeTab === 'details' && <DetailsTab />}
      </div>
    </div>
  );
}
