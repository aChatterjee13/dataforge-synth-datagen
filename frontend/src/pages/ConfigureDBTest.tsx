import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Database, Sparkles, Key, Settings } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/Card';
import { Button } from '../components/Button';
import ErrorBanner from '../components/ErrorBanner';
import { generateDBTests } from '../services/api';
import { getApiErrorMessage } from '../lib/utils';

const SQL_DIALECTS = [
  { value: 'postgresql', label: 'PostgreSQL' },
  { value: 'mysql', label: 'MySQL' },
  { value: 'sqlite', label: 'SQLite' },
  { value: 'sqlserver', label: 'SQL Server' },
  { value: 'oracle', label: 'Oracle' },
];

export default function ConfigureDBTest() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const [numRowsPerTable, setNumRowsPerTable] = useState(100);
  const [sqlDialect, setSqlDialect] = useState('postgresql');
  const [generateViolations, setGenerateViolations] = useState(true);
  const [generatePerformance, setGeneratePerformance] = useState(false);
  const [gptModel, setGptModel] = useState('gpt-4o-mini');
  const [useEnvKey, setUseEnvKey] = useState(true);
  const [apiKey, setApiKey] = useState('');
  const [gptEndpoint, setGptEndpoint] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const config = {
        model_type: 'gpt_data_test',
        num_rows: 0,
        epochs: 0,
        batch_size: 0,
        data_type: 'data_testing',
        num_rows_per_table: numRowsPerTable,
        sql_dialect: sqlDialect,
        generate_violations: generateViolations,
        generate_performance: generatePerformance,
        gpt_model: gptModel,
        gpt_api_key: useEnvKey ? null : (apiKey || null),
        gpt_endpoint: gptEndpoint || null,
      };

      await generateDBTests(jobId!, config);
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
          ← Back to Upload
        </Button>
        <h1 className="text-3xl font-bold mb-2">Configure Database Test Generation</h1>
        <p className="text-gray-600">Set up LLM-powered test data generation from your schema</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Data Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Database className="h-5 w-5 mr-2 text-amber-600" />
              Data Settings
            </CardTitle>
            <CardDescription>Configure the generated test data</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Rows per Table
              </label>
              <input
                type="number"
                min="1"
                max="10000"
                value={numRowsPerTable}
                onChange={e => setNumRowsPerTable(parseInt(e.target.value) || 100)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
              />
              <p className="text-xs text-gray-500 mt-1">
                Number of INSERT rows to generate per table (1 - 10,000)
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                SQL Dialect
              </label>
              <select
                value={sqlDialect}
                onChange={e => setSqlDialect(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
              >
                {SQL_DIALECTS.map(d => (
                  <option key={d.value} value={d.value}>{d.label}</option>
                ))}
              </select>
            </div>
          </CardContent>
        </Card>

        {/* Test Options */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Settings className="h-5 w-5 mr-2 text-amber-600" />
              Test Options
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <label className="flex items-start p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
              <input
                type="checkbox"
                checked={generateViolations}
                onChange={e => setGenerateViolations(e.target.checked)}
                className="mt-1 mr-3"
              />
              <div>
                <div className="font-medium text-sm">Constraint Violation Tests</div>
                <div className="text-xs text-gray-500">
                  Generate INSERTs that intentionally violate NOT NULL, UNIQUE, FK, and CHECK constraints
                </div>
              </div>
            </label>

            <label className="flex items-start p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
              <input
                type="checkbox"
                checked={generatePerformance}
                onChange={e => setGeneratePerformance(e.target.checked)}
                className="mt-1 mr-3"
              />
              <div>
                <div className="font-medium text-sm">Performance / Load Data</div>
                <div className="text-xs text-gray-500">
                  Generate larger datasets suitable for performance testing
                </div>
              </div>
            </label>
          </CardContent>
        </Card>

        {/* GPT Model */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Sparkles className="h-5 w-5 mr-2 text-amber-600" />
              GPT Model Selection
            </CardTitle>
          </CardHeader>
          <CardContent>
            <select
              value={gptModel}
              onChange={e => setGptModel(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
            >
              <optgroup label="Recommended">
                <option value="gpt-4o-mini">GPT-4o Mini (Fast & Reliable)</option>
                <option value="gpt-4o">GPT-4o (Best Quality)</option>
              </optgroup>
              <optgroup label="Latest Models">
                <option value="gpt-5-mini">GPT-5 Mini</option>
                <option value="gpt-5">GPT-5</option>
              </optgroup>
              <optgroup label="Other">
                <option value="gpt-4-turbo">GPT-4 Turbo</option>
                <option value="gpt-3.5-turbo">GPT-3.5 Turbo (Budget)</option>
              </optgroup>
            </select>
          </CardContent>
        </Card>

        {/* API Key */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Key className="h-5 w-5 mr-2 text-amber-600" />
              API Key Configuration
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={useEnvKey}
                onChange={e => setUseEnvKey(e.target.checked)}
                className="mr-2"
              />
              <span className="text-sm font-medium text-gray-700">
                Use environment variable (OPENAI_API_KEY)
              </span>
            </label>
            {!useEnvKey && (
              <input
                type="password"
                value={apiKey}
                onChange={e => setApiKey(e.target.value)}
                placeholder="sk-..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
              />
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                API Endpoint (Optional)
              </label>
              <input
                type="text"
                value={gptEndpoint}
                onChange={e => setGptEndpoint(e.target.value)}
                placeholder="https://api.openai.com/v1/chat/completions"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
              />
            </div>
          </CardContent>
        </Card>

        {/* Info */}
        <Card className="bg-amber-50 border-amber-200">
          <CardContent className="pt-6">
            <div className="flex items-start">
              <Settings className="h-5 w-5 text-amber-700 mr-3 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-amber-900">
                <p className="font-semibold mb-2">How Database Test Generation Works</p>
                <ul className="space-y-1 text-xs">
                  <li>- Parses your schema to understand tables & relationships</li>
                  <li>- Computes dependency order for foreign key references</li>
                  <li>- Uses GPT to generate realistic INSERT statements</li>
                  <li>- Validates output with an in-memory SQLite dry-run</li>
                </ul>
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
            Generate Test Data
          </Button>
        </div>
      </form>
    </div>
  );
}
