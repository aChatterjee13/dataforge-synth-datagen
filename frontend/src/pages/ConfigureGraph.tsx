import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Share2, Settings, Plus, RefreshCw } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/Card';
import { Button } from '../components/Button';
import ErrorBanner from '../components/ErrorBanner';
import { generateGraph } from '../services/api';
import { getApiErrorMessage } from '../lib/utils';
import type { GraphStatsInfo } from '../types';

const GRAPH_MODELS = [
  { value: 'auto', label: 'Auto (Recommended)' },
  { value: 'barabasi_albert', label: 'Barabasi-Albert' },
  { value: 'erdos_renyi', label: 'Erdos-Renyi' },
  { value: 'watts_strogatz', label: 'Watts-Strogatz' },
  { value: 'stochastic_block', label: 'Stochastic Block Model' },
];

const OUTPUT_FORMATS = [
  { value: 'csv', label: 'CSV' },
  { value: 'json', label: 'JSON' },
  { value: 'graphml', label: 'GraphML' },
  { value: 'gexf', label: 'GEXF' },
];

export default function ConfigureGraph() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const [graphStats, setGraphStats] = useState<GraphStatsInfo | null>(null);
  const [graphMode, setGraphMode] = useState<'generate' | 'augment'>('generate');
  const [graphModel, setGraphModel] = useState('auto');
  const [targetNodes, setTargetNodes] = useState(100);
  const [targetEdges, setTargetEdges] = useState<number | ''>('');
  const [additionalNodes, setAdditionalNodes] = useState(10);
  const [additionalEdges, setAdditionalEdges] = useState(20);
  const [outputFormat, setOutputFormat] = useState('csv');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const stored = sessionStorage.getItem(`graph_stats_${jobId}`);
    if (stored) {
      try {
        const stats: GraphStatsInfo = JSON.parse(stored);
        setGraphStats(stats);
        setTargetNodes(stats.nodes);
      } catch {
        // ignore parse errors
      }
    }
  }, [jobId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const config: Record<string, unknown> = {
        model_type: 'graph_synth',
        num_rows: 0,
        epochs: 0,
        batch_size: 0,
        data_type: 'graph_synthesis',
        graph_mode: graphMode,
        graph_output_format: outputFormat,
      };

      if (graphMode === 'augment') {
        config.graph_additional_nodes = additionalNodes;
        config.graph_additional_edges = additionalEdges;
      } else {
        config.graph_model = graphModel;
        config.graph_target_nodes = targetNodes;
        config.graph_target_edges = targetEdges || null;
      }

      await generateGraph(jobId!, config);
      navigate(`/generate/${jobId}`);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err));
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}
      <div className="mb-8">
        <Button variant="outline" onClick={() => navigate('/')} className="mb-4">
          &larr; Back to Upload
        </Button>
        <h1 className="text-3xl font-bold mb-2">Configure Graph Synthesis</h1>
        <p className="text-gray-600">Set up synthetic graph generation from your network data</p>
      </div>

      {/* Original Graph Stats */}
      {graphStats && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center">
              <Share2 className="h-5 w-5 mr-2 text-amber-600" />
              Original Graph Statistics
            </CardTitle>
            <CardDescription>Properties detected from your uploaded graph</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <div className="text-2xl font-bold text-amber-600">{graphStats.nodes.toLocaleString()}</div>
                <div className="text-xs text-gray-600">Nodes</div>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">{graphStats.edges.toLocaleString()}</div>
                <div className="text-xs text-gray-600">Edges</div>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <div className="text-2xl font-bold text-purple-600">{graphStats.density.toFixed(4)}</div>
                <div className="text-xs text-gray-600">Density</div>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600">{graphStats.avg_degree.toFixed(2)}</div>
                <div className="text-xs text-gray-600">Avg Degree</div>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <div className="text-2xl font-bold text-indigo-600">{graphStats.clustering_coefficient.toFixed(4)}</div>
                <div className="text-xs text-gray-600">Clustering Coefficient</div>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <div className="text-2xl font-bold text-orange-600">{graphStats.connected_components}</div>
                <div className="text-xs text-gray-600">Connected Components</div>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded-lg col-span-2">
                <div className="text-2xl font-bold text-gray-700">
                  {graphStats.is_directed ? 'Directed' : 'Undirected'}
                </div>
                <div className="text-xs text-gray-600">Graph Type</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Mode Toggle */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Settings className="h-5 w-5 mr-2 text-amber-600" />
              Mode
            </CardTitle>
            <CardDescription>Choose whether to generate a new graph or augment the existing one</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setGraphMode('generate')}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border-2 font-medium transition-colors ${
                  graphMode === 'generate'
                    ? 'border-amber-500 bg-amber-50 text-amber-800'
                    : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
                }`}
              >
                <RefreshCw className="h-4 w-4" />
                Generate New
              </button>
              <button
                type="button"
                onClick={() => setGraphMode('augment')}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border-2 font-medium transition-colors ${
                  graphMode === 'augment'
                    ? 'border-amber-500 bg-amber-50 text-amber-800'
                    : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
                }`}
              >
                <Plus className="h-4 w-4" />
                Augment Existing
              </button>
            </div>
          </CardContent>
        </Card>

        {/* Model Selection — only for Generate mode */}
        {graphMode === 'generate' && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Share2 className="h-5 w-5 mr-2 text-amber-600" />
                Model Selection
              </CardTitle>
              <CardDescription>Choose the graph generation model</CardDescription>
            </CardHeader>
            <CardContent>
              <select
                value={graphModel}
                onChange={e => setGraphModel(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
              >
                {GRAPH_MODELS.map(m => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
              <p className="text-xs text-gray-500 mt-2">
                Auto mode selects the best model based on graph properties
              </p>
            </CardContent>
          </Card>
        )}

        {/* Generation Parameters */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Settings className="h-5 w-5 mr-2 text-amber-600" />
              {graphMode === 'augment' ? 'Augmentation Parameters' : 'Generation Parameters'}
            </CardTitle>
            <CardDescription>
              {graphMode === 'augment'
                ? 'Configure how many nodes and edges to add to the existing graph'
                : 'Configure the synthetic graph size and output'}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {graphMode === 'generate' ? (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Target Nodes
                  </label>
                  <input
                    type="number"
                    min="10"
                    max="100000"
                    value={targetNodes}
                    onChange={e => setTargetNodes(parseInt(e.target.value) || 100)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Number of nodes in the synthetic graph (10 - 100,000)
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Target Edges (Optional)
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={targetEdges}
                    onChange={e => setTargetEdges(e.target.value ? parseInt(e.target.value) : '')}
                    placeholder="Auto-determined from model"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Leave blank to let the model determine edge count based on graph properties
                  </p>
                </div>
              </>
            ) : (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Additional Nodes
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="100000"
                    value={additionalNodes}
                    onChange={e => setAdditionalNodes(parseInt(e.target.value) || 0)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Number of new nodes to add to the graph (0 - 100,000)
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Additional Edges
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="500000"
                    value={additionalEdges}
                    onChange={e => setAdditionalEdges(parseInt(e.target.value) || 0)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Number of new edges to add between nodes (0 - 500,000)
                  </p>
                </div>
              </>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Output Format
              </label>
              <select
                value={outputFormat}
                onChange={e => setOutputFormat(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
              >
                {OUTPUT_FORMATS.map(f => (
                  <option key={f.value} value={f.value}>{f.label}</option>
                ))}
              </select>
            </div>
          </CardContent>
        </Card>

        {/* Info */}
        <Card className="bg-amber-50 border-amber-200">
          <CardContent className="pt-6">
            <div className="flex items-start">
              <Share2 className="h-5 w-5 text-amber-700 mr-3 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-amber-900">
                {graphMode === 'augment' ? (
                  <>
                    <p className="font-semibold mb-2">How Graph Augmentation Works</p>
                    <ul className="space-y-1 text-xs">
                      <li>- Preserves all original nodes, edges, and their attributes</li>
                      <li>- New nodes connect via preferential attachment biased toward detected communities</li>
                      <li>- Extra edges use triadic closure to preserve clustering patterns</li>
                      <li>- Node and edge attributes are sampled from original distributions</li>
                    </ul>
                  </>
                ) : (
                  <>
                    <p className="font-semibold mb-2">How Graph Synthesis Works</p>
                    <ul className="space-y-1 text-xs">
                      <li>- Analyzes structural properties of your original graph</li>
                      <li>- Selects a generative model that best preserves topology</li>
                      <li>- Generates a synthetic graph matching degree distributions, clustering, and density</li>
                      <li>- Compares original vs synthetic statistics for quality validation</li>
                    </ul>
                  </>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Submit */}
        <div className="flex gap-4">
          <Button type="button" variant="outline" onClick={() => navigate('/')} className="flex-1">
            Cancel
          </Button>
          <Button type="submit" className="flex-1 bg-amber-600 hover:bg-amber-700">
            {graphMode === 'augment' ? 'Augment Graph' : 'Generate Graph'}
          </Button>
        </div>
      </form>
    </div>
  );
}
