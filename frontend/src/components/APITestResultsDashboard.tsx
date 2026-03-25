import { useState } from 'react';
import { Download, ChevronDown, ChevronRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './Card';
import { Button } from './Button';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { downloadAPITests } from '../services/api';
import type { APITestResultsResponse } from '../types';

interface Props {
  jobId: string;
  results: APITestResultsResponse;
}

const METHOD_COLORS: Record<string, string> = {
  GET: 'bg-green-100 text-green-800',
  POST: 'bg-blue-100 text-blue-800',
  PUT: 'bg-amber-100 text-amber-800',
  PATCH: 'bg-orange-100 text-orange-800',
  DELETE: 'bg-red-100 text-red-800',
};

const CATEGORY_COLORS: Record<string, string> = {
  positive: 'bg-green-100 text-green-800',
  negative: 'bg-red-100 text-red-800',
  edge_case: 'bg-yellow-100 text-yellow-800',
  security: 'bg-purple-100 text-purple-800',
  relationship: 'bg-blue-100 text-blue-800',
  rate_limit: 'bg-orange-100 text-orange-800',
  pagination: 'bg-cyan-100 text-cyan-800',
  idempotency: 'bg-gray-100 text-gray-800',
};

export default function APITestResultsDashboard({ jobId, results }: Props) {
  const [expandedTests, setExpandedTests] = useState<Set<number>>(new Set());

  const toggleTest = (index: number) => {
    setExpandedTests(prev => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  const categoryChartData = Object.entries(results.category_counts).map(([name, count]) => ({
    name: name.replace('_', ' '),
    count,
  }));

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-green-600">{results.summary.total_tests}</div>
            <div className="text-sm text-gray-600">Total Tests</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-blue-600">{results.summary.endpoints_covered}</div>
            <div className="text-sm text-gray-600">Endpoints Covered</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-purple-600">{Object.keys(results.category_counts).length}</div>
            <div className="text-sm text-gray-600">Categories</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-amber-600">{results.summary.total_flows}</div>
            <div className="text-sm text-gray-600">Flow Tests</div>
          </CardContent>
        </Card>
      </div>

      {/* Endpoint Coverage Table */}
      <Card>
        <CardHeader>
          <CardTitle>Endpoint Coverage</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 px-3">Endpoint</th>
                  <th className="text-right py-2 px-3">Tests</th>
                </tr>
              </thead>
              <tbody>
                {results.endpoint_coverage.map((ep, i) => {
                  const parts = ep.endpoint.split(' ');
                  const method = parts[0] || '';
                  const path = parts.slice(1).join(' ') || ep.endpoint;
                  const colorClass = METHOD_COLORS[method] || 'bg-gray-100 text-gray-800';

                  return (
                    <tr key={i} className="border-b hover:bg-gray-50">
                      <td className="py-2 px-3">
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-mono font-bold mr-2 ${colorClass}`}>
                          {method}
                        </span>
                        <span className="font-mono text-gray-700">{path}</span>
                      </td>
                      <td className="text-right py-2 px-3 font-medium">{ep.test_count}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Category Breakdown Chart */}
      {categoryChartData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Category Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categoryChartData} layout="vertical" margin={{ left: 80 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis type="category" dataKey="name" />
                  <Tooltip />
                  <Bar dataKey="count" fill="#22c55e" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Sample Tests */}
      <Card>
        <CardHeader>
          <CardTitle>Sample Tests</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {results.sample_tests.map((test, i) => {
              const isExpanded = expandedTests.has(i);
              const category = test.category || 'general';
              const method = test.method || 'GET';
              const name = test.name || 'Unnamed Test';
              const catColor = CATEGORY_COLORS[category] || 'bg-gray-100 text-gray-800';
              const methodColor = METHOD_COLORS[method] || 'bg-gray-100 text-gray-800';

              return (
                <div key={i} className="border rounded-lg">
                  <button
                    onClick={() => toggleTest(i)}
                    className="w-full flex items-center justify-between p-3 hover:bg-gray-50 text-left"
                  >
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${methodColor}`}>
                        {method}
                      </span>
                      <span className={`px-2 py-0.5 rounded text-xs ${catColor}`}>
                        {category}
                      </span>
                      <span className="text-sm font-medium">{name}</span>
                    </div>
                    {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                  </button>
                  {isExpanded && (
                    <div className="px-3 pb-3 border-t bg-gray-50">
                      <p className="text-sm text-gray-600 mt-2">{test.description || 'No description'}</p>
                      <div className="mt-2 text-xs font-mono">
                        <span className="text-gray-500">Path:</span> {test.path || '/'}
                      </div>
                      {test.expected && (
                        <div className="mt-1 text-xs font-mono">
                          <span className="text-gray-500">Expected Status:</span>{' '}
                          <span className="font-bold">{test.expected.status_code}</span>
                        </div>
                      )}
                      {test.request && Object.keys(test.request).length > 0 && (
                        <pre className="mt-2 p-2 bg-white rounded text-xs overflow-x-auto border">
                          {JSON.stringify(test.request, null, 2)}
                        </pre>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Download Buttons */}
      <Card>
        <CardContent className="p-6">
          <div className="flex gap-4">
            <a
              href={downloadAPITests(jobId, 'postman')}
              className="flex-1"
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button className="w-full bg-green-600 hover:bg-green-700">
                <Download className="h-4 w-4 mr-2" />
                Download Postman Collection
              </Button>
            </a>
            <a
              href={downloadAPITests(jobId, 'json')}
              className="flex-1"
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button variant="outline" className="w-full">
                <Download className="h-4 w-4 mr-2" />
                Download JSON Suite
              </Button>
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
