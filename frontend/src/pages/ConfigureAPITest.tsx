import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Zap, Sparkles, Key, Settings } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/Card';
import { Button } from '../components/Button';
import ErrorBanner from '../components/ErrorBanner';
import { generateAPITests } from '../services/api';
import { getApiErrorMessage } from '../lib/utils';

const TEST_CATEGORIES = [
  { id: 'positive', label: 'Positive Tests', description: 'Valid requests matching schema' },
  { id: 'negative', label: 'Negative Tests', description: 'Missing fields, wrong types' },
  { id: 'edge_case', label: 'Edge Cases', description: 'Boundary values, special chars' },
  { id: 'security', label: 'Security Tests', description: 'SQL injection, XSS, auth' },
  { id: 'relationship', label: 'Relationship Tests', description: 'Cross-endpoint CRUD flows' },
  { id: 'rate_limit', label: 'Rate Limiting', description: 'Burst request patterns' },
  { id: 'pagination', label: 'Pagination Tests', description: 'Invalid page/offset combos' },
  { id: 'idempotency', label: 'Idempotency Tests', description: 'Repeated identical requests' },
];

export default function ConfigureAPITest() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const [selectedCategories, setSelectedCategories] = useState<string[]>(['positive', 'negative']);
  const [baseUrl, setBaseUrl] = useState('');
  const [gptModel, setGptModel] = useState('gpt-4o-mini');
  const [useEnvKey, setUseEnvKey] = useState(true);
  const [apiKey, setApiKey] = useState('');
  const [gptEndpoint, setGptEndpoint] = useState('');
  const [error, setError] = useState<string | null>(null);

  const toggleCategory = (id: string) => {
    setSelectedCategories(prev =>
      prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (selectedCategories.length === 0) {
      setError('Please select at least one test category');
      return;
    }

    try {
      const config = {
        model_type: 'gpt_api_test',
        num_rows: 0,
        epochs: 0,
        batch_size: 0,
        data_type: 'api_testing',
        test_categories: selectedCategories,
        output_format: 'postman',
        base_url: baseUrl || null,
        gpt_model: gptModel,
        gpt_api_key: useEnvKey ? null : (apiKey || null),
        gpt_endpoint: gptEndpoint || null,
      };

      await generateAPITests(jobId!, config);
      navigate(`/generate/${jobId}`);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err));
    }
  };

  const estimatedTests = selectedCategories.length * 5;

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}
      <div className="mb-8">
        <Button variant="outline" onClick={() => navigate('/')} className="mb-4">
          ← Back to Upload
        </Button>
        <h1 className="text-3xl font-bold mb-2">Configure API Test Generation</h1>
        <p className="text-gray-600">Set up LLM-powered API test suite generation</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Test Categories */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Zap className="h-5 w-5 mr-2 text-green-600" />
              Test Categories
            </CardTitle>
            <CardDescription>
              Select which types of tests to generate
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3">
              {TEST_CATEGORIES.map(cat => (
                <label
                  key={cat.id}
                  className={`flex items-start p-3 border rounded-lg cursor-pointer transition-colors ${
                    selectedCategories.includes(cat.id)
                      ? 'border-green-500 bg-green-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedCategories.includes(cat.id)}
                    onChange={() => toggleCategory(cat.id)}
                    className="mt-1 mr-3"
                  />
                  <div>
                    <div className="font-medium text-sm">{cat.label}</div>
                    <div className="text-xs text-gray-500">{cat.description}</div>
                  </div>
                </label>
              ))}
            </div>
            <p className="text-sm text-gray-500 mt-4">
              Estimated: ~{estimatedTests} tests per endpoint
            </p>
          </CardContent>
        </Card>

        {/* Base URL */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Settings className="h-5 w-5 mr-2 text-green-600" />
              Output Settings
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Base URL (Optional)
              </label>
              <input
                type="text"
                value={baseUrl}
                onChange={e => setBaseUrl(e.target.value)}
                placeholder="https://api.example.com"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
              />
              <p className="text-xs text-gray-500 mt-1">
                Pre-fills the Postman collection base URL. Leave empty to use the spec's server URL.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* GPT Model Selection */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Sparkles className="h-5 w-5 mr-2 text-green-600" />
              GPT Model Selection
            </CardTitle>
          </CardHeader>
          <CardContent>
            <select
              value={gptModel}
              onChange={e => setGptModel(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
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
              <Key className="h-5 w-5 mr-2 text-green-600" />
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
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
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
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
              />
            </div>
          </CardContent>
        </Card>

        {/* Info */}
        <Card className="bg-green-50 border-green-200">
          <CardContent className="pt-6">
            <div className="flex items-start">
              <Settings className="h-5 w-5 text-green-700 mr-3 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-green-900">
                <p className="font-semibold mb-2">How API Test Generation Works</p>
                <ul className="space-y-1 text-xs">
                  <li>- Parses your OpenAPI spec to understand endpoints & schemas</li>
                  <li>- Detects CRUD relationships between endpoints</li>
                  <li>- Uses GPT to generate test cases per category</li>
                  <li>- Outputs a ready-to-import Postman collection</li>
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
          <Button type="submit" className="flex-1 bg-green-600 hover:bg-green-700">
            Generate API Tests
          </Button>
        </div>
      </form>
    </div>
  );
}
