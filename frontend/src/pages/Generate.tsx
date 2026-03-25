import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Loader2, CheckCircle2, XCircle, Eye } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/Card';
import { Button } from '../components/Button';
import LivePreview from '../components/LivePreview';
import { getJobStatus } from '../services/api';
import { JobStatus, type JobStatusResponse } from '../types';

export default function Generate() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [status, setStatus] = useState<JobStatusResponse | null>(null);
  const [polling, setPolling] = useState(true);
  const [showPreview, setShowPreview] = useState(false);

  useEffect(() => {
    if (!jobId) return;

    const pollStatus = async () => {
      try {
        const response = await getJobStatus(jobId);
        setStatus(response);

        if (response.status === JobStatus.COMPLETED) {
          setPolling(false);
          // Redirect to appropriate results page based on model type
          setTimeout(() => {
            if (response.model_type === 'gpt_pdf') {
              navigate(`/pdf-results/${jobId}`);
            } else if (response.model_type === 'gpt_api_test') {
              navigate(`/api-test-results/${jobId}`);
            } else if (response.model_type === 'gpt_data_test') {
              navigate(`/db-test-results/${jobId}`);
            } else if (response.model_type === 'pii_mask') {
              navigate(`/pii-results/${jobId}`);
            } else if (response.model_type === 'log_synth') {
              navigate(`/log-results/${jobId}`);
            } else if (response.model_type === 'cdc_gen') {
              navigate(`/cdc-results/${jobId}`);
            } else if (response.model_type === 'graph_synth') {
              navigate(`/graph-results/${jobId}`);
            } else {
              navigate(`/results/${jobId}`);
            }
          }, 2000);
        } else if (response.status === JobStatus.FAILED) {
          setPolling(false);
        }
      } catch (error) {
        console.error('Failed to fetch status:', error);
      }
    };

    // Initial poll
    pollStatus();

    // Poll every 2 seconds if still processing
    const interval = setInterval(() => {
      if (polling) {
        pollStatus();
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [jobId, polling, navigate]);

  if (!status) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-2xl">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold mb-2">Generating Synthetic Data</h1>
        <p className="text-gray-600">Please wait while we generate your synthetic dataset</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            {status.status === JobStatus.PROCESSING && (
              <Loader2 className="h-6 w-6 mr-2 animate-spin text-blue-600" />
            )}
            {status.status === JobStatus.COMPLETED && (
              <CheckCircle2 className="h-6 w-6 mr-2 text-green-600" />
            )}
            {status.status === JobStatus.FAILED && (
              <XCircle className="h-6 w-6 mr-2 text-red-600" />
            )}
            {status.status === JobStatus.PROCESSING && 'Processing...'}
            {status.status === JobStatus.COMPLETED && 'Completed!'}
            {status.status === JobStatus.FAILED && 'Failed'}
          </CardTitle>
          <CardDescription>{status.message}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-600">Progress</span>
              <span className="font-medium">{Math.round(status.progress)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div
                className={`h-3 rounded-full transition-all duration-500 ${
                  status.status === JobStatus.COMPLETED
                    ? 'bg-green-600'
                    : status.status === JobStatus.FAILED
                    ? 'bg-red-600'
                    : 'bg-blue-600'
                }`}
                style={{ width: `${status.progress}%` }}
              />
            </div>
          </div>

          {status.status === JobStatus.PROCESSING && (
            <div className="space-y-4">
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-blue-800 text-sm">
                  This may take several minutes depending on your dataset size and configuration.
                  Don't close this page.
                </p>
              </div>

              {/* Live Preview Toggle (Feature 12) */}
              <div>
                <button
                  onClick={() => setShowPreview(!showPreview)}
                  className="flex items-center text-sm font-medium text-blue-600 hover:text-blue-800"
                >
                  <Eye className="h-4 w-4 mr-1" />
                  {showPreview ? 'Hide Live Preview' : 'Show Live Preview'}
                </button>
                {showPreview && jobId && (
                  <div className="mt-3">
                    <LivePreview jobId={jobId} isGenerating={polling} />
                  </div>
                )}
              </div>
            </div>
          )}

          {status.status === JobStatus.COMPLETED && (
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-green-800 font-medium">
                Synthetic data generated successfully!
              </p>
              <p className="text-green-700 text-sm mt-1">Redirecting to results...</p>
            </div>
          )}

          {status.status === JobStatus.FAILED && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-800 font-medium mb-2">Generation failed</p>
              {status.error && (
                <p className="text-red-700 text-sm font-mono whitespace-pre-wrap">
                  {status.error}
                </p>
              )}
              <Button
                variant="outline"
                onClick={() => navigate('/')}
                className="mt-4"
              >
                Start Over
              </Button>
            </div>
          )}

          <div className="pt-4 border-t text-sm text-gray-500">
            <div className="flex justify-between">
              <span>Job ID:</span>
              <span className="font-mono">{jobId?.slice(0, 8)}...</span>
            </div>
            <div className="flex justify-between mt-2">
              <span>Started:</span>
              <span>{new Date(status.created_at).toLocaleString()}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
