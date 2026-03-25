import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { Button } from '../components/Button';
import DBTestResultsDashboard from '../components/DBTestResultsDashboard';
import { getDBTestResults } from '../services/api';
import { getApiErrorMessage } from '../lib/utils';
import type { DBTestResultsResponse } from '../types';

export default function DBTestResults() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [results, setResults] = useState<DBTestResultsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!jobId) return;

    const fetchResults = async () => {
      try {
        const data = await getDBTestResults(jobId);
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
      <div className="container mx-auto px-4 py-8 max-w-6xl flex justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-amber-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800 font-medium">Error loading results</p>
          <p className="text-red-600 text-sm">{error}</p>
        </div>
        <Button onClick={() => navigate('/')} className="mt-4">Back to Home</Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="mb-8">
        <Button variant="outline" onClick={() => navigate('/')} className="mb-4">
          ← Back to Home
        </Button>
        <h1 className="text-3xl font-bold mb-2">Database Test Results</h1>
        <p className="text-gray-600">
          Generated test data ({results?.summary.dialect || 'SQL'} dialect)
        </p>
      </div>

      {results && <DBTestResultsDashboard jobId={jobId!} results={results} />}
    </div>
  );
}
