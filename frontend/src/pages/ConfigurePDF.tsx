import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { FileText, Sparkles, Key, Settings } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/Card';
import { Button } from '../components/Button';
import ErrorBanner from '../components/ErrorBanner';
import { generatePDFs } from '../services/api';
import { getApiErrorMessage } from '../lib/utils';
import type { GenerationConfig, ModelType } from '../types';

export default function ConfigurePDF() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const [config, setConfig] = useState<GenerationConfig>({
    model_type: 'gpt_pdf' as ModelType,
    num_rows: 0, // Not used for PDFs
    epochs: 0, // Not used for PDFs
    batch_size: 0, // Not used for PDFs
    data_type: 'unstructured',
    num_pdfs: 5,
    gpt_model: 'gpt-4o-mini', // Default to GPT-4o Mini (reliable and fast)
    gpt_api_key: '',
    gpt_endpoint: ''
  });

  const [useEnvKey, setUseEnvKey] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      // Only send PDF-relevant fields to avoid serialization issues
      const pdfConfig = {
        model_type: config.model_type,
        num_rows: 0,  // Required by backend but not used for PDFs
        epochs: 0,    // Required by backend but not used for PDFs
        batch_size: 0, // Required by backend but not used for PDFs
        // PDF-specific fields
        num_pdfs: config.num_pdfs || 5,
        gpt_model: config.gpt_model || 'gpt-4o-mini',
        gpt_api_key: useEnvKey ? null : (config.gpt_api_key || null),
        gpt_endpoint: config.gpt_endpoint || null
      };

      await generatePDFs(jobId!, pdfConfig);

      // Navigate to generation progress page
      navigate(`/generate/${jobId}`);
    } catch (err: unknown) {
      console.error('Generation error:', err);
      setError(getApiErrorMessage(err));
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}
      <div className="mb-8">
        <Button
          variant="outline"
          onClick={() => navigate('/')}
          className="mb-4"
        >
          ← Back to Upload
        </Button>
        <h1 className="text-3xl font-bold mb-2">Configure PDF Generation</h1>
        <p className="text-gray-600">Set up GPT-powered synthetic PDF generation</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Number of PDFs */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <FileText className="h-5 w-5 mr-2 text-purple-600" />
              Generation Settings
            </CardTitle>
            <CardDescription>
              Configure how many synthetic PDFs to generate
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Number of PDFs per Sample
              </label>
              <input
                type="number"
                min="1"
                max="20"
                value={config.num_pdfs}
                onChange={(e) => setConfig({ ...config, num_pdfs: parseInt(e.target.value) })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
              <p className="text-sm text-gray-500 mt-1">
                Generate {config.num_pdfs || 5} synthetic PDF{(config.num_pdfs || 5) > 1 ? 's' : ''} for each uploaded sample
              </p>
            </div>
          </CardContent>
        </Card>

        {/* GPT Model Selection */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Sparkles className="h-5 w-5 mr-2 text-purple-600" />
              GPT Model Selection
            </CardTitle>
            <CardDescription>
              Choose the GPT model for content generation
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                GPT Model
              </label>
              <select
                value={config.gpt_model}
                onChange={(e) => setConfig({ ...config, gpt_model: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                <optgroup label="Recommended (Most Reliable)">
                  <option value="gpt-4o-mini">GPT-4o Mini ⭐ (Recommended - Fast, Reliable & High Quality)</option>
                  <option value="gpt-4o">GPT-4o (Best Quality, Slower)</option>
                </optgroup>
                <optgroup label="Latest Models (GPT-5 Series - Experimental)">
                  <option value="gpt-5-mini">GPT-5 Mini (Latest, May be slower)</option>
                  <option value="gpt-5-nano">GPT-5 Nano (Fastest)</option>
                  <option value="gpt-5">GPT-5 (Full Model)</option>
                </optgroup>
                <optgroup label="Reasoning Models (Advanced)">
                  <option value="o1-mini">o1-mini (Advanced Reasoning)</option>
                  <option value="o1-preview">o1-preview (Maximum Reasoning)</option>
                </optgroup>
                <optgroup label="Other Models">
                  <option value="gpt-4-turbo">GPT-4 Turbo</option>
                  <option value="gpt-4">GPT-4 (Classic)</option>
                  <option value="gpt-3.5-turbo">GPT-3.5 Turbo (Budget)</option>
                </optgroup>
              </select>
              <p className="text-sm text-gray-500 mt-1">
                <strong>GPT-4o Mini</strong> is recommended for reliable PDF generation with good quality. GPT-5 models are newer but may be slower.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* API Key Configuration */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Key className="h-5 w-5 mr-2 text-purple-600" />
              API Key Configuration
            </CardTitle>
            <CardDescription>
              Configure OpenAI API access
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={useEnvKey}
                  onChange={(e) => setUseEnvKey(e.target.checked)}
                  className="mr-2"
                />
                <span className="text-sm font-medium text-gray-700">
                  Use environment variable (OPENAI_API_KEY)
                </span>
              </label>
              <p className="text-xs text-gray-500 mt-1 ml-6">
                Recommended for security. Set OPENAI_API_KEY in backend environment.
              </p>
            </div>

            {!useEnvKey && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  OpenAI API Key
                </label>
                <input
                  type="password"
                  value={config.gpt_api_key}
                  onChange={(e) => setConfig({ ...config, gpt_api_key: e.target.value })}
                  placeholder="sk-..."
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Your API key is sent securely and not stored permanently
                </p>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                API Endpoint (Optional)
              </label>
              <input
                type="text"
                value={config.gpt_endpoint}
                onChange={(e) => setConfig({ ...config, gpt_endpoint: e.target.value })}
                placeholder="https://api.openai.com/v1/chat/completions"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
              <p className="text-xs text-gray-500 mt-1">
                Leave empty to use default OpenAI endpoint
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Info Box */}
        <Card className="bg-purple-50 border-purple-200">
          <CardContent className="pt-6">
            <div className="flex items-start">
              <Settings className="h-5 w-5 text-purple-700 mr-3 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-purple-900">
                <p className="font-semibold mb-2">How PDF Generation Works</p>
                <ul className="space-y-1 text-xs">
                  <li>• Analyzes structure and style of uploaded PDFs</li>
                  <li>• Uses GPT to generate similar content with different details</li>
                  <li>• Preserves document type, tone, and format</li>
                  <li>• Creates completely new content (privacy-safe)</li>
                  <li>• Generates professional PDFs with proper formatting</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Submit Button */}
        <div className="flex gap-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate('/')}
            className="flex-1"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            className="flex-1 bg-purple-600 hover:bg-purple-700"
          >
            Start PDF Generation
          </Button>
        </div>
      </form>
    </div>
  );
}
