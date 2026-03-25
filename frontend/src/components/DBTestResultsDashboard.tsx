import { useState } from 'react';
import { Download, ChevronDown, ChevronRight, CheckCircle, XCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './Card';
import { Button } from './Button';
import { downloadDBTests } from '../services/api';
import type { DBTestResultsResponse } from '../types';

interface Props {
  jobId: string;
  results: DBTestResultsResponse;
}

const CONSTRAINT_COLORS: Record<string, string> = {
  not_null: 'bg-red-100 text-red-800',
  unique: 'bg-purple-100 text-purple-800',
  foreign_key: 'bg-blue-100 text-blue-800',
  data_type: 'bg-amber-100 text-amber-800',
  check: 'bg-orange-100 text-orange-800',
};

export default function DBTestResultsDashboard({ jobId, results }: Props) {
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());

  const toggleTable = (name: string) => {
    setExpandedTables(prev => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const validationScore = results.validation?.validation_score ?? 0;
  const scoreColor = validationScore >= 0.9 ? 'text-green-600' : validationScore >= 0.7 ? 'text-amber-600' : 'text-red-600';

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-amber-600">{results.summary.total_tables}</div>
            <div className="text-sm text-gray-600">Tables Covered</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-blue-600">{results.summary.total_inserts}</div>
            <div className="text-sm text-gray-600">Total Inserts</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-purple-600">{results.summary.total_violations}</div>
            <div className="text-sm text-gray-600">Violation Tests</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className={`text-3xl font-bold ${scoreColor}`}>
              {(validationScore * 100).toFixed(0)}%
            </div>
            <div className="text-sm text-gray-600">Validation Score</div>
          </CardContent>
        </Card>
      </div>

      {/* Dependency Flow */}
      {results.dependency_order && results.dependency_order.length > 1 && (
        <Card>
          <CardHeader>
            <CardTitle>Insert Dependency Order</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap items-center gap-2">
              {results.dependency_order.map((table, i) => (
                <div key={table} className="flex items-center">
                  <div className="px-3 py-1.5 bg-amber-100 border border-amber-300 rounded-lg text-sm font-mono font-medium">
                    {table}
                  </div>
                  {i < results.dependency_order!.length - 1 && (
                    <span className="mx-1 text-gray-400 font-bold">→</span>
                  )}
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Tables are inserted in this order to satisfy foreign key constraints
            </p>
          </CardContent>
        </Card>
      )}

      {/* Table Details */}
      <Card>
        <CardHeader>
          <CardTitle>Table Details</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {Object.entries(results.table_details).map(([name, details]) => {
              const isExpanded = expandedTables.has(name);

              return (
                <div key={name} className="border rounded-lg">
                  <button
                    onClick={() => toggleTable(name)}
                    className="w-full flex items-center justify-between p-3 hover:bg-gray-50 text-left"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-mono font-bold text-sm">{name}</span>
                      <span className="text-xs text-gray-500">
                        {details.insert_count} inserts, {details.columns} cols
                      </span>
                      {details.foreign_keys.length > 0 && (
                        <span className="text-xs text-blue-600">
                          FK → {details.foreign_keys.join(', ')}
                        </span>
                      )}
                    </div>
                    {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                  </button>
                  {isExpanded && (
                    <div className="px-3 pb-3 border-t bg-gray-50 space-y-3">
                      {/* Sample INSERTs */}
                      {results.sample_inserts?.[name] && results.sample_inserts[name].length > 0 && (
                        <div className="mt-2">
                          <div className="text-xs font-medium text-gray-700 mb-1">Sample INSERTs:</div>
                          <pre className="p-2 bg-white rounded text-xs overflow-x-auto border font-mono">
                            {results.sample_inserts[name].join('\n')}
                          </pre>
                        </div>
                      )}

                      {/* Sample Violations */}
                      {results.sample_violations?.[name] && (results.sample_violations[name] as any[]).length > 0 && (
                        <div>
                          <div className="text-xs font-medium text-gray-700 mb-1">Violation Tests:</div>
                          {(results.sample_violations[name] as any[]).map((v: any, vi: number) => (
                            <div key={vi} className="p-2 bg-white rounded border mb-1">
                              <div className="flex items-center gap-2 mb-1">
                                <span className={`px-2 py-0.5 rounded text-xs ${CONSTRAINT_COLORS[v.constraint_type] || 'bg-gray-100 text-gray-800'}`}>
                                  {v.constraint_type}
                                </span>
                                <span className="text-xs font-medium">{v.name}</span>
                              </div>
                              <p className="text-xs text-gray-600">{v.description}</p>
                              <pre className="mt-1 text-xs font-mono text-red-700">{v.sql}</pre>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Validation Details */}
      {results.validation && (
        <Card>
          <CardHeader>
            <CardTitle>SQLite Dry-Run Validation</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="text-center">
                <div className="text-lg font-bold text-gray-800">{results.validation.total}</div>
                <div className="text-xs text-gray-500">Total Statements</div>
              </div>
              <div className="text-center">
                <div className="flex items-center justify-center gap-1">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <span className="text-lg font-bold text-green-600">{results.validation.successful}</span>
                </div>
                <div className="text-xs text-gray-500">Successful</div>
              </div>
              <div className="text-center">
                <div className="flex items-center justify-center gap-1">
                  <XCircle className="h-4 w-4 text-red-600" />
                  <span className="text-lg font-bold text-red-600">{results.validation.failed}</span>
                </div>
                <div className="text-xs text-gray-500">Failed</div>
              </div>
            </div>

            {results.validation.errors.length > 0 && (
              <div className="mt-2">
                <div className="text-xs font-medium text-gray-700 mb-1">Errors (first {Math.min(results.validation.errors.length, 5)}):</div>
                <div className="space-y-1">
                  {results.validation.errors.slice(0, 5).map((err, i) => (
                    <div key={i} className="text-xs text-red-700 font-mono p-1 bg-red-50 rounded">
                      {err}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Download Buttons */}
      <Card>
        <CardContent className="p-6">
          <div className="flex gap-4">
            <a href={downloadDBTests(jobId, 'all')} className="flex-1" target="_blank" rel="noopener noreferrer">
              <Button className="w-full bg-amber-600 hover:bg-amber-700">
                <Download className="h-4 w-4 mr-2" />
                Download All (ZIP)
              </Button>
            </a>
            <a href={downloadDBTests(jobId, 'inserts')} className="flex-1" target="_blank" rel="noopener noreferrer">
              <Button variant="outline" className="w-full">
                <Download className="h-4 w-4 mr-2" />
                Inserts Only
              </Button>
            </a>
            <a href={downloadDBTests(jobId, 'violations')} className="flex-1" target="_blank" rel="noopener noreferrer">
              <Button variant="outline" className="w-full">
                <Download className="h-4 w-4 mr-2" />
                Violations Only
              </Button>
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
