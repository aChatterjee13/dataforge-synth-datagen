import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Settings as SettingsIcon,
  Key,
  Plus,
  Trash2,
  Copy,
  ArrowLeft,
  Loader2,
  Check,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/Card';
import { Button } from '../components/Button';
import { createAPIKey, listAPIKeys, deleteAPIKey } from '../services/api';
import type { APIKeyItem, APIKeyCreateResponse } from '../types';

export default function Settings() {
  const navigate = useNavigate();

  // --- API Key State ---
  const [keys, setKeys] = useState<APIKeyItem[]>([]);
  const [loadingKeys, setLoadingKeys] = useState(true);
  const [keysError, setKeysError] = useState<string | null>(null);

  const [newKeyName, setNewKeyName] = useState('');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const [newlyCreatedKey, setNewlyCreatedKey] = useState<APIKeyCreateResponse | null>(null);
  const [copied, setCopied] = useState(false);

  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  // --- Fetch keys on mount ---
  const fetchKeys = useCallback(async () => {
    setLoadingKeys(true);
    setKeysError(null);
    try {
      const data = await listAPIKeys();
      setKeys(data);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to load API keys';
      setKeysError(message);
    } finally {
      setLoadingKeys(false);
    }
  }, []);

  useEffect(() => {
    fetchKeys();
  }, [fetchKeys]);

  // --- Create key ---
  const handleCreate = async () => {
    const trimmed = newKeyName.trim();
    if (!trimmed) return;

    setCreating(true);
    setCreateError(null);
    setNewlyCreatedKey(null);

    try {
      const created = await createAPIKey(trimmed);
      setNewlyCreatedKey(created);
      setNewKeyName('');
      await fetchKeys();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to create API key';
      setCreateError(message);
    } finally {
      setCreating(false);
    }
  };

  // --- Copy key to clipboard ---
  const handleCopy = async (key: string) => {
    try {
      await navigator.clipboard.writeText(key);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = key;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // --- Delete key ---
  const handleDelete = async (keyId: number) => {
    if (confirmDeleteId !== keyId) {
      setConfirmDeleteId(keyId);
      return;
    }

    setDeletingId(keyId);
    try {
      await deleteAPIKey(keyId);
      setConfirmDeleteId(null);
      await fetchKeys();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to delete API key';
      setKeysError(message);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Button variant="ghost" size="sm" onClick={() => navigate('/')}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Home
          </Button>
        </div>

        <div className="flex items-center gap-3 mb-8">
          <SettingsIcon className="w-8 h-8 text-blue-600" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
            <p className="text-gray-500">
              Manage API keys, webhooks, and view API documentation
            </p>
          </div>
        </div>

        {/* ================================================================
            SECTION 1: API Key Management
        ================================================================ */}
        <Card className="mb-8">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Key className="w-5 h-5 text-blue-600" />
              <CardTitle className="text-xl">API Key Management</CardTitle>
            </div>
            <CardDescription>
              Create and manage API keys for programmatic access to DataForge.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-6">
            {/* Create new key form */}
            <div className="flex items-end gap-3">
              <div className="flex-1">
                <label
                  htmlFor="key-name"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Key Name
                </label>
                <input
                  id="key-name"
                  type="text"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleCreate();
                  }}
                  placeholder="e.g. production-pipeline"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <Button
                onClick={handleCreate}
                disabled={creating || !newKeyName.trim()}
              >
                {creating ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Plus className="w-4 h-4 mr-2" />
                )}
                Create New Key
              </Button>
            </div>

            {createError && (
              <div className="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-700">
                {createError}
              </div>
            )}

            {/* Newly created key banner */}
            {newlyCreatedKey && (
              <div className="rounded-md bg-green-50 border border-green-200 p-4">
                <p className="text-sm font-semibold text-green-800 mb-2">
                  API key created successfully! Copy it now -- it will not be
                  shown again.
                </p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 rounded bg-white border border-green-300 px-3 py-2 text-sm font-mono text-green-900 select-all">
                    {newlyCreatedKey.key}
                  </code>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleCopy(newlyCreatedKey.key)}
                  >
                    {copied ? (
                      <>
                        <Check className="w-4 h-4 mr-1 text-green-600" />
                        Copied
                      </>
                    ) : (
                      <>
                        <Copy className="w-4 h-4 mr-1" />
                        Copy
                      </>
                    )}
                  </Button>
                </div>
                <p className="text-xs text-green-700 mt-2">
                  Store this key securely. For security, the full key cannot be
                  retrieved after you leave this page.
                </p>
              </div>
            )}

            {/* Existing keys table */}
            {loadingKeys ? (
              <div className="flex items-center justify-center py-8 text-gray-500">
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                Loading API keys...
              </div>
            ) : keysError ? (
              <div className="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-700">
                {keysError}
              </div>
            ) : keys.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <Key className="w-10 h-10 mx-auto mb-2 text-gray-300" />
                <p>No API keys yet. Create one above to get started.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 text-left">
                      <th className="py-3 pr-4 font-medium text-gray-600">
                        Name
                      </th>
                      <th className="py-3 pr-4 font-medium text-gray-600">
                        Key Preview
                      </th>
                      <th className="py-3 pr-4 font-medium text-gray-600">
                        Created At
                      </th>
                      <th className="py-3 pr-4 font-medium text-gray-600">
                        Last Used
                      </th>
                      <th className="py-3 font-medium text-gray-600 text-right">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {keys.map((item) => (
                      <tr
                        key={item.id}
                        className="border-b border-gray-100 hover:bg-gray-50"
                      >
                        <td className="py-3 pr-4 font-medium text-gray-900">
                          {item.name}
                        </td>
                        <td className="py-3 pr-4">
                          <code className="rounded bg-gray-100 px-2 py-0.5 text-xs font-mono text-gray-600">
                            {item.key_preview}
                          </code>
                        </td>
                        <td className="py-3 pr-4 text-gray-500">
                          {new Date(item.created_at).toLocaleDateString()}
                        </td>
                        <td className="py-3 pr-4 text-gray-500">
                          {item.last_used
                            ? new Date(item.last_used).toLocaleDateString()
                            : 'Never'}
                        </td>
                        <td className="py-3 text-right">
                          <Button
                            variant={
                              confirmDeleteId === item.id
                                ? 'destructive'
                                : 'ghost'
                            }
                            size="sm"
                            disabled={deletingId === item.id}
                            onClick={() => handleDelete(item.id)}
                            onBlur={() => {
                              if (confirmDeleteId === item.id) {
                                setConfirmDeleteId(null);
                              }
                            }}
                          >
                            {deletingId === item.id ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : confirmDeleteId === item.id ? (
                              'Confirm Delete'
                            ) : (
                              <Trash2 className="w-4 h-4 text-red-500" />
                            )}
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* ================================================================
            SECTION 2: Webhook Documentation
        ================================================================ */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="text-xl">Webhook Notifications</CardTitle>
            <CardDescription>
              Get notified when synthetic data generation completes by
              configuring a webhook URL in your generation request.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-5">
            <div>
              <h3 className="text-sm font-semibold text-gray-800 mb-2">
                How It Works
              </h3>
              <ol className="list-decimal list-inside text-sm text-gray-600 space-y-1">
                <li>
                  Add a <code className="text-blue-700 bg-blue-50 px-1 rounded">webhook_url</code> field
                  to your generation config.
                </li>
                <li>
                  DataForge will send a <code className="text-blue-700 bg-blue-50 px-1 rounded">POST</code> request
                  to your URL when generation completes.
                </li>
                <li>
                  Your server receives the payload with job details and
                  generation status.
                </li>
              </ol>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-gray-800 mb-2">
                Example: Trigger Generation with Webhook
              </h3>
              <pre className="rounded-md bg-gray-900 text-gray-100 p-4 text-xs overflow-x-auto leading-relaxed">
{`curl -X POST http://localhost:8000/api/generate \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: your-api-key" \\
  -d '{
    "job_id": "...",
    "config": {
      "model_type": "auto",
      "num_rows": 1000,
      "epochs": 300,
      "batch_size": 500,
      "webhook_url": "https://your-server.com/webhook"
    }
  }'`}
              </pre>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-gray-800 mb-2">
                Example: Webhook Payload
              </h3>
              <p className="text-sm text-gray-600 mb-2">
                When generation finishes, DataForge will POST the following JSON
                to your webhook URL:
              </p>
              <pre className="rounded-md bg-gray-900 text-gray-100 p-4 text-xs overflow-x-auto leading-relaxed">
{`{
  "event": "generation.completed",
  "job_id": "abc-123-def",
  "status": "completed",
  "created_at": "2025-10-13T10:30:00Z",
  "completed_at": "2025-10-13T10:35:12Z",
  "model_type": "ctgan",
  "rows_generated": 1000,
  "quality_score": 0.87,
  "download_url": "http://localhost:8000/api/download/abc-123-def"
}`}
              </pre>
            </div>
          </CardContent>
        </Card>

        {/* ================================================================
            SECTION 3: API Documentation
        ================================================================ */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="text-xl">API Reference</CardTitle>
            <CardDescription>
              A quick overview of the main DataForge API endpoints. All
              endpoints accept and return JSON unless otherwise noted.
            </CardDescription>
          </CardHeader>

          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 text-left">
                    <th className="py-2 pr-4 font-medium text-gray-600">
                      Method
                    </th>
                    <th className="py-2 pr-4 font-medium text-gray-600">
                      Endpoint
                    </th>
                    <th className="py-2 font-medium text-gray-600">
                      Description
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  <tr>
                    <td className="py-2 pr-4">
                      <span className="inline-block rounded bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700">
                        POST
                      </span>
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs text-gray-800">
                      /api/upload
                    </td>
                    <td className="py-2 text-gray-600">
                      Upload a dataset (CSV or Excel) for processing.
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">
                      <span className="inline-block rounded bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700">
                        POST
                      </span>
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs text-gray-800">
                      /api/generate
                    </td>
                    <td className="py-2 text-gray-600">
                      Start synthetic data generation for an uploaded job.
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">
                      <span className="inline-block rounded bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">
                        GET
                      </span>
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs text-gray-800">
                      /api/status/:job_id
                    </td>
                    <td className="py-2 text-gray-600">
                      Check the progress and status of a generation job.
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">
                      <span className="inline-block rounded bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">
                        GET
                      </span>
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs text-gray-800">
                      /api/download/:job_id
                    </td>
                    <td className="py-2 text-gray-600">
                      Download the generated synthetic dataset.
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">
                      <span className="inline-block rounded bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">
                        GET
                      </span>
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs text-gray-800">
                      /api/validation/:job_id
                    </td>
                    <td className="py-2 text-gray-600">
                      Retrieve validation metrics comparing original and
                      synthetic data.
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">
                      <span className="inline-block rounded bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">
                        GET
                      </span>
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs text-gray-800">
                      /api/jobs
                    </td>
                    <td className="py-2 text-gray-600">
                      List all generation jobs with their statuses.
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">
                      <span className="inline-block rounded bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700">
                        POST
                      </span>
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs text-gray-800">
                      /api/api-keys
                    </td>
                    <td className="py-2 text-gray-600">
                      Create a new API key for programmatic access.
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">
                      <span className="inline-block rounded bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">
                        GET
                      </span>
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs text-gray-800">
                      /api/api-keys
                    </td>
                    <td className="py-2 text-gray-600">
                      List all API keys (key values are masked).
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">
                      <span className="inline-block rounded bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">
                        DELETE
                      </span>
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs text-gray-800">
                      /api/api-keys/:id
                    </td>
                    <td className="py-2 text-gray-600">
                      Revoke and delete an API key.
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">
                      <span className="inline-block rounded bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">
                        GET
                      </span>
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs text-gray-800">
                      /api/recommend/:job_id
                    </td>
                    <td className="py-2 text-gray-600">
                      Get a model recommendation for an uploaded dataset.
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">
                      <span className="inline-block rounded bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700">
                        POST
                      </span>
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs text-gray-800">
                      /api/compare
                    </td>
                    <td className="py-2 text-gray-600">
                      Compare two datasets and receive validation metrics.
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">
                      <span className="inline-block rounded bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700">
                        POST
                      </span>
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs text-gray-800">
                      /api/drift-detect
                    </td>
                    <td className="py-2 text-gray-600">
                      Detect statistical drift between a baseline and snapshot
                      dataset.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="mt-6 rounded-md bg-blue-50 border border-blue-200 p-4 text-sm text-blue-800">
              <p className="font-semibold mb-1">Authentication</p>
              <p>
                Include your API key in the{' '}
                <code className="bg-blue-100 px-1 rounded">X-API-Key</code>{' '}
                request header for all programmatic requests.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Back to Home button */}
        <div className="flex justify-center pb-8">
          <Button variant="outline" onClick={() => navigate('/')}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Home
          </Button>
        </div>
      </div>
    </div>
  );
}
