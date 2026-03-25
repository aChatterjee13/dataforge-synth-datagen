import { useEffect, useState } from 'react';
import { GitBranch, Download } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from './Card';
import { Button } from './Button';
import { getCDCResults, downloadCDC } from '../services/api';
import { getApiErrorMessage } from '../lib/utils';
import type { CDCResultsResponse } from '../types';

interface Props {
  jobId: string;
}

export default function CDCResultsDashboard({ jobId }: Props) {
  const [results, setResults] = useState<CDCResultsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchResults = async () => {
      try {
        const data = await getCDCResults(jobId);
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
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-600 border-t-transparent" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-red-800 font-medium">Error loading CDC results</p>
        <p className="text-red-600 text-sm">{error}</p>
      </div>
    );
  }

  if (!results) return null;

  const { summary, sample_events } = results;

  const chartData = [
    { operation: 'INSERT', count: summary.inserts, fill: '#22c55e' },
    { operation: 'UPDATE', count: summary.updates, fill: '#3b82f6' },
    { operation: 'DELETE', count: summary.deletes, fill: '#ef4444' },
  ];

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-amber-600">{summary.total_events}</div>
            <div className="text-sm text-gray-600">Total Events</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-green-600">{summary.inserts}</div>
            <div className="text-sm text-gray-600">Inserts</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-blue-600">{summary.updates}</div>
            <div className="text-sm text-gray-600">Updates</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-red-600">{summary.deletes}</div>
            <div className="text-sm text-gray-600">Deletes</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-purple-600">{summary.tables_affected}</div>
            <div className="text-sm text-gray-600">Tables Affected</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-lg font-bold text-gray-700 capitalize">{summary.output_format}</div>
            <div className="text-sm text-gray-600">Output Format</div>
          </CardContent>
        </Card>
      </div>

      {/* Event Distribution Bar Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <GitBranch className="h-5 w-5 mr-2 text-amber-600" />
            Event Distribution by Operation
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="operation" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" name="Events">
                {chartData.map((entry, index) => (
                  <rect key={index} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Sample Events */}
      {sample_events && sample_events.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <GitBranch className="h-5 w-5 mr-2 text-amber-600" />
              Sample Events
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="bg-gray-900 rounded-lg p-4 overflow-auto max-h-[500px]">
              <pre className="text-sm text-green-400 font-mono whitespace-pre-wrap">
                {JSON.stringify(sample_events.slice(0, 5), null, 2)}
              </pre>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Showing first {Math.min(5, sample_events.length)} of {summary.total_events} events
            </p>
          </CardContent>
        </Card>
      )}

      {/* Download */}
      <Card>
        <CardContent className="p-6">
          <a href={downloadCDC(jobId)} target="_blank" rel="noopener noreferrer">
            <Button className="w-full bg-amber-600 hover:bg-amber-700">
              <Download className="h-4 w-4 mr-2" />
              Download CDC Events
            </Button>
          </a>
        </CardContent>
      </Card>
    </div>
  );
}
