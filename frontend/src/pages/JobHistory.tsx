import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { History, Trash2, Eye, Filter, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/Card';
import { Button } from '../components/Button';
import { listJobs, deleteJob } from '../services/api';
import { getApiErrorMessage } from '../lib/utils';
import ErrorBanner from '../components/ErrorBanner';
import type { JobListItem } from '../types';
import { JobStatus } from '../types';

type StatusFilter = 'all' | 'completed' | 'processing' | 'failed';

const STATUS_BADGE_CLASSES: Record<string, string> = {
  [JobStatus.COMPLETED]: 'bg-green-100 text-green-800',
  [JobStatus.PROCESSING]: 'bg-blue-100 text-blue-800',
  [JobStatus.PENDING]: 'bg-gray-100 text-gray-800',
  [JobStatus.FAILED]: 'bg-red-100 text-red-800',
};

function getResultsPath(jobId: string, modelType?: string): string {
  switch (modelType) {
    case 'gpt_pdf':
      return `/pdf-results/${jobId}`;
    case 'gpt_api_test':
      return `/api-test-results/${jobId}`;
    case 'gpt_data_test':
      return `/db-test-results/${jobId}`;
    default:
      return `/results/${jobId}`;
  }
}

function formatDate(dateString: string): string {
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateString;
  }
}

export default function JobHistory() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [dataTypeFilter, setDataTypeFilter] = useState<string>('all');
  const [deletingJobId, setDeletingJobId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const fetchJobs = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listJobs();
      setJobs(data);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const handleDelete = async (jobId: string) => {
    const confirmed = window.confirm(
      'Are you sure you want to delete this job? This action cannot be undone.'
    );
    if (!confirmed) return;

    try {
      setDeletingJobId(jobId);
      await deleteJob(jobId);
      setJobs((prev) => prev.filter((job) => job.job_id !== jobId));
    } catch (err: unknown) {
      setDeleteError(getApiErrorMessage(err));
    } finally {
      setDeletingJobId(null);
    }
  };

  const handleView = (job: JobListItem) => {
    const path = getResultsPath(job.job_id, job.model_type);
    navigate(path);
  };

  // Derive unique data types from model_type field for filter dropdown
  const dataTypes = Array.from(
    new Set(jobs.map((job) => job.model_type || 'unknown').filter(Boolean))
  );

  const filteredJobs = jobs.filter((job) => {
    if (statusFilter !== 'all' && job.status !== statusFilter) {
      return false;
    }
    if (dataTypeFilter !== 'all' && (job.model_type || 'unknown') !== dataTypeFilter) {
      return false;
    }
    return true;
  });

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          <p className="text-lg text-gray-600">Loading job history...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <Card>
          <CardContent className="p-8 text-center">
            <p className="text-red-600 mb-4">{error}</p>
            <div className="flex gap-3 justify-center">
              <Button onClick={fetchJobs}>Retry</Button>
              <Button variant="outline" onClick={() => navigate('/')}>
                Back to Home
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {deleteError && <ErrorBanner message={deleteError} onDismiss={() => setDeleteError(null)} />}
      {/* Header */}
      <div className="mb-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="flex items-center gap-3">
          <History className="h-8 w-8 text-blue-600" />
          <div>
            <h1 className="text-3xl font-bold">Job History</h1>
            <p className="text-gray-600">View and manage all your generation jobs</p>
          </div>
        </div>
        <Button variant="outline" onClick={() => navigate('/')}>
          Back to Home
        </Button>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700">Filters:</span>
            </div>
            <div className="flex flex-wrap gap-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Status</label>
                <select
                  className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
                >
                  <option value="all">All</option>
                  <option value="completed">Completed</option>
                  <option value="processing">Processing</option>
                  <option value="failed">Failed</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Data Type</label>
                <select
                  className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={dataTypeFilter}
                  onChange={(e) => setDataTypeFilter(e.target.value)}
                >
                  <option value="all">All</option>
                  {dataTypes.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="sm:ml-auto text-sm text-gray-500">
              {filteredJobs.length} of {jobs.length} jobs
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Jobs Table */}
      <Card>
        <CardHeader>
          <CardTitle>Jobs ({filteredJobs.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {filteredJobs.length === 0 ? (
            <div className="text-center py-12">
              <History className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500 text-lg mb-2">No jobs found</p>
              <p className="text-gray-400 text-sm">
                {jobs.length === 0
                  ? 'You have not created any generation jobs yet.'
                  : 'No jobs match the selected filters.'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b-2 border-gray-300">
                    <th className="text-left py-3 px-3 font-medium text-gray-700">Filename</th>
                    <th className="text-left py-3 px-3 font-medium text-gray-700">Status</th>
                    <th className="text-left py-3 px-3 font-medium text-gray-700">Model Type</th>
                    <th className="text-right py-3 px-3 font-medium text-gray-700">Quality Score</th>
                    <th className="text-right py-3 px-3 font-medium text-gray-700">Rows</th>
                    <th className="text-left py-3 px-3 font-medium text-gray-700">Created At</th>
                    <th className="text-center py-3 px-3 font-medium text-gray-700">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredJobs.map((job) => (
                    <tr
                      key={job.job_id}
                      className="border-b border-gray-200 hover:bg-gray-50 transition-colors"
                    >
                      <td className="py-3 px-3">
                        <div className="font-medium text-gray-900 truncate max-w-xs" title={job.filename}>
                          {job.filename}
                        </div>
                        <div className="text-xs text-gray-400 truncate max-w-xs" title={job.job_id}>
                          {job.job_id}
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            STATUS_BADGE_CLASSES[job.status] || 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {job.status}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-gray-600">
                        {job.model_type || '-'}
                      </td>
                      <td className="py-3 px-3 text-right">
                        {job.quality_score != null ? (
                          <span
                            className={`font-semibold ${
                              job.quality_score >= 0.8
                                ? 'text-green-600'
                                : job.quality_score >= 0.6
                                ? 'text-yellow-600'
                                : 'text-red-600'
                            }`}
                          >
                            {Math.round(job.quality_score * 100)}%
                          </span>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-right text-gray-600">
                        {job.rows_original != null
                          ? job.rows_original.toLocaleString()
                          : '-'}
                      </td>
                      <td className="py-3 px-3 text-gray-600">
                        {formatDate(job.created_at)}
                      </td>
                      <td className="py-3 px-3">
                        <div className="flex items-center justify-center gap-2">
                          <button
                            onClick={() => handleView(job)}
                            className="p-1.5 rounded-md text-blue-600 hover:bg-blue-50 transition-colors"
                            title="View Results"
                            disabled={job.status !== JobStatus.COMPLETED}
                          >
                            <Eye
                              className={`h-4 w-4 ${
                                job.status !== JobStatus.COMPLETED
                                  ? 'opacity-30'
                                  : ''
                              }`}
                            />
                          </button>
                          <button
                            onClick={() => handleDelete(job.job_id)}
                            className="p-1.5 rounded-md text-red-600 hover:bg-red-50 transition-colors"
                            title="Delete Job"
                            disabled={deletingJobId === job.job_id}
                          >
                            {deletingJobId === job.job_id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Trash2 className="h-4 w-4" />
                            )}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
