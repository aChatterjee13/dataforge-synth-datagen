import { useState, useEffect } from 'react';
import { Share2, Download, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './Card';
import { Button } from './Button';
import NetworkGraph from './NetworkGraph';
import { getGraphResults, downloadGraph } from '../services/api';
import { getApiErrorMessage } from '../lib/utils';
import type { GraphResultsResponse } from '../types';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  Legend,
} from 'recharts';

interface Props {
  jobId: string;
}

const COMPARISON_METRICS = [
  { key: 'nodes', label: 'Nodes' },
  { key: 'edges', label: 'Edges' },
  { key: 'density', label: 'Density' },
  { key: 'avg_degree', label: 'Avg Degree' },
  { key: 'clustering_coefficient', label: 'Clustering Coefficient' },
];

export default function GraphResultsDashboard({ jobId }: Props) {
  const [results, setResults] = useState<GraphResultsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchResults = async () => {
      try {
        const data = await getGraphResults(jobId);
        setResults(data);
      } catch (err: unknown) {
        setError(getApiErrorMessage(err));
      } finally {
        setLoading(false);
      }
    };

    fetchResults();
  }, [jobId]);

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-amber-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-red-800 font-medium">Error loading results</p>
        <p className="text-red-600 text-sm">{error}</p>
      </div>
    );
  }

  if (!results) return null;

  const isAugment = results.summary.mode === 'augment';
  const resultLabel = isAugment ? 'Augmented' : 'Synthetic';

  const matchScore = results.summary.overall_match_score;
  const scoreColor =
    matchScore >= 0.8
      ? 'bg-green-100 text-green-800'
      : matchScore >= 0.5
        ? 'bg-yellow-100 text-yellow-800'
        : 'bg-red-100 text-red-800';

  // Build degree distribution chart data
  const degreeDistData: Array<Record<string, unknown>> = [];
  const origStats = results.original_stats as Record<string, unknown>;
  const synthStats = results.synthetic_stats as Record<string, unknown>;
  const origDist = origStats.degree_distribution as Record<string, number> | undefined;
  const synthDist = synthStats.degree_distribution as Record<string, number> | undefined;

  if (origDist && synthDist) {
    const allDegrees = new Set<string>();
    Object.keys(origDist).forEach(k => allDegrees.add(k));
    Object.keys(synthDist).forEach(k => allDegrees.add(k));

    const sorted = Array.from(allDegrees)
      .map(d => parseInt(d))
      .sort((a, b) => a - b);

    sorted.forEach(degree => {
      degreeDistData.push({
        degree: String(degree),
        Original: origDist[String(degree)] || 0,
        [resultLabel]: synthDist[String(degree)] || 0,
      });
    });
  }

  const graphData = results.graph_data;

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {isAugment ? (
          <>
            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-sm font-medium text-gray-600 mb-2">
                  Structural Preservation
                </div>
                <span className={`inline-block px-3 py-1 rounded-full text-lg font-bold ${scoreColor}`}>
                  {(matchScore * 100).toFixed(1)}%
                </span>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-3xl font-bold text-green-600">
                  +{(results.summary.nodes_added ?? 0).toLocaleString()}
                </div>
                <div className="text-sm text-gray-600">Nodes Added</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-3xl font-bold text-blue-600">
                  +{(results.summary.edges_added ?? 0).toLocaleString()}
                </div>
                <div className="text-sm text-gray-600">Edges Added</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-3xl font-bold text-amber-600">
                  {results.summary.synthetic_nodes.toLocaleString()}
                </div>
                <div className="text-sm text-gray-600">Total Nodes</div>
              </CardContent>
            </Card>
          </>
        ) : (
          <>
            <Card>
              <CardContent className="p-4 text-center">
                <div className="flex items-center justify-center mb-2">
                  <Share2 className="h-5 w-5 text-amber-600" />
                </div>
                <div className="text-sm font-medium text-gray-600">Model Used</div>
                <div className="text-lg font-bold text-gray-900 mt-1">
                  {results.summary.model_used}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-sm font-medium text-gray-600 mb-2">Overall Match Score</div>
                <span className={`inline-block px-3 py-1 rounded-full text-lg font-bold ${scoreColor}`}>
                  {(matchScore * 100).toFixed(1)}%
                </span>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-3xl font-bold text-amber-600">
                  {results.summary.synthetic_nodes.toLocaleString()}
                </div>
                <div className="text-sm text-gray-600">Synthetic Nodes</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-3xl font-bold text-blue-600">
                  {results.summary.synthetic_edges.toLocaleString()}
                </div>
                <div className="text-sm text-gray-600">Synthetic Edges</div>
              </CardContent>
            </Card>
          </>
        )}
      </div>

      {/* Graph Visualization: Original vs Synthetic/Augmented */}
      {graphData && (
        <Card>
          <CardHeader>
            <CardTitle>Network Topology: Original vs {resultLabel}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <NetworkGraph
                data={graphData.original}
                label="Original Graph"
                nodeColor="#f59e0b"
                edgeColor="#fbbf24"
              />
              <NetworkGraph
                data={graphData.synthetic}
                label={`${resultLabel} Graph`}
                nodeColor="#3b82f6"
                edgeColor="#93c5fd"
              />
            </div>
            <p className="text-xs text-gray-400 mt-4 text-center">
              Node size reflects degree (number of connections). Hover over nodes for details.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Original vs Synthetic/Augmented Comparison Table */}
      <Card>
        <CardHeader>
          <CardTitle>Original vs {resultLabel} Comparison</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-4 font-semibold text-gray-700">Metric</th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700">Original</th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700">{resultLabel}</th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700">Match Score</th>
                </tr>
              </thead>
              <tbody>
                {COMPARISON_METRICS.map(metric => {
                  const comp = results.comparison[metric.key];
                  if (!comp) return null;

                  const cellScoreColor =
                    comp.match_score >= 0.8
                      ? 'text-green-600'
                      : comp.match_score >= 0.5
                        ? 'text-yellow-600'
                        : 'text-red-600';

                  const isIntegerMetric = metric.key === 'nodes' || metric.key === 'edges';

                  return (
                    <tr key={metric.key} className="border-b last:border-b-0 hover:bg-gray-50">
                      <td className="py-3 px-4 font-medium text-gray-900">{metric.label}</td>
                      <td className="py-3 px-4 text-right font-mono">
                        {isIntegerMetric
                          ? comp.original.toLocaleString()
                          : comp.original.toFixed(4)}
                      </td>
                      <td className="py-3 px-4 text-right font-mono">
                        {isIntegerMetric
                          ? comp.synthetic.toLocaleString()
                          : comp.synthetic.toFixed(4)}
                      </td>
                      <td className={`py-3 px-4 text-right font-bold ${cellScoreColor}`}>
                        {(comp.match_score * 100).toFixed(1)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Degree Distribution Chart */}
      {degreeDistData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Degree Distribution Comparison</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={degreeDistData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="degree"
                    label={{ value: 'Degree', position: 'insideBottom', offset: -5 }}
                  />
                  <YAxis
                    label={{ value: 'Count', angle: -90, position: 'insideLeft' }}
                  />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="Original" fill="#f59e0b" opacity={0.7} />
                  <Bar dataKey={resultLabel} fill="#3b82f6" opacity={0.7} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Download */}
      <Card>
        <CardContent className="p-6">
          <a href={downloadGraph(jobId)} target="_blank" rel="noopener noreferrer" className="block">
            <Button className="w-full bg-amber-600 hover:bg-amber-700">
              <Download className="h-4 w-4 mr-2" />
              Download {resultLabel} Graph
            </Button>
          </a>
        </CardContent>
      </Card>
    </div>
  );
}
