import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Network, Play, ArrowLeft, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/Card';
import { Button } from '../components/Button';
import RelationshipBuilder from '../components/RelationshipBuilder';
import { generateMultiTable } from '../services/api';
import type { TableRelationship, MultiTableUploadResponse } from '../types';

const ConfigureMultiTable: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const [tableInfo, setTableInfo] = useState<MultiTableUploadResponse | null>(null);
  const [relationships, setRelationships] = useState<TableRelationship[]>([]);
  const [numRows, setNumRows] = useState<number>(1000);
  const [epochs, setEpochs] = useState<number>(300);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) {
      setError('No job ID provided.');
      return;
    }

    const stored = sessionStorage.getItem(`multi_table_${jobId}`);
    if (stored) {
      try {
        const parsed: MultiTableUploadResponse = JSON.parse(stored);
        setTableInfo(parsed);
      } catch {
        setError('Failed to load table information from session storage.');
      }
    } else {
      setError('No multi-table upload data found. Please upload your tables first.');
    }
  }, [jobId]);

  const handleGenerate = async () => {
    if (!jobId) return;

    setIsGenerating(true);
    setError(null);

    try {
      await generateMultiTable(jobId, {
        relationships,
        num_rows: numRows,
        epochs,
      });
      navigate(`/generate/${jobId}`);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : 'Failed to start multi-table generation. Please try again.';
      setError(message);
      setIsGenerating(false);
    }
  };

  if (error && !tableInfo) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <Card className="max-w-lg w-full">
          <CardHeader>
            <CardTitle className="text-red-600">Error</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600 mb-4">{error}</p>
            <Button variant="outline" onClick={() => navigate(-1)}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Go Back
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!tableInfo) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  const tableNames = Object.keys(tableInfo.tables);

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => navigate(-1)}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <div className="flex items-center gap-3">
            <Network className="w-8 h-8 text-blue-600" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Configure Multi-Table Generation
              </h1>
              <p className="text-sm text-gray-500">
                Define relationships between tables and configure generation parameters
              </p>
            </div>
          </div>
        </div>

        {/* Table Summary Cards */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Uploaded Tables</CardTitle>
            <CardDescription>
              {tableNames.length} table{tableNames.length !== 1 ? 's' : ''} detected
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {tableNames.map((tableName) => {
                const table = tableInfo.tables[tableName];
                return (
                  <div
                    key={tableName}
                    className="border rounded-lg p-4 bg-gray-50 hover:bg-gray-100 transition-colors"
                  >
                    <h3 className="font-semibold text-gray-900 truncate" title={tableName}>
                      {tableName}
                    </h3>
                    <div className="mt-2 space-y-1 text-sm text-gray-600">
                      <p>
                        <span className="font-medium">{table.rows.toLocaleString()}</span> rows
                      </p>
                      <p>
                        <span className="font-medium">{table.columns}</span> columns
                      </p>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {Object.keys(table.column_types).slice(0, 4).map((col) => (
                        <span
                          key={col}
                          className="inline-block text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded"
                        >
                          {col}
                        </span>
                      ))}
                      {Object.keys(table.column_types).length > 4 && (
                        <span className="inline-block text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded">
                          +{Object.keys(table.column_types).length - 4} more
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Relationship Builder */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Table Relationships</CardTitle>
            <CardDescription>
              Define foreign key relationships between your tables to preserve referential integrity
            </CardDescription>
          </CardHeader>
          <CardContent>
            <RelationshipBuilder
              tables={tableInfo.tables}
              relationships={relationships}
              onRelationshipsChange={setRelationships}
            />
          </CardContent>
        </Card>

        {/* Configuration */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Generation Parameters</CardTitle>
            <CardDescription>
              Adjust the number of rows and training epochs for synthetic data generation
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div>
                <label
                  htmlFor="num-rows"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Number of Rows
                </label>
                <input
                  id="num-rows"
                  type="number"
                  min={1}
                  value={numRows}
                  onChange={(e) => setNumRows(Math.max(1, parseInt(e.target.value, 10) || 1))}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Number of synthetic rows to generate per table
                </p>
              </div>
              <div>
                <label
                  htmlFor="epochs"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Training Epochs
                </label>
                <input
                  id="epochs"
                  type="number"
                  min={1}
                  value={epochs}
                  onChange={(e) => setEpochs(Math.max(1, parseInt(e.target.value, 10) || 1))}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <p className="mt-1 text-xs text-gray-500">
                  More epochs may improve quality but increase generation time
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Error Message */}
        {error && (
          <div className="rounded-md bg-red-50 border border-red-200 p-4">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Generate Button */}
        <div className="flex justify-end">
          <Button
            size="lg"
            onClick={handleGenerate}
            disabled={isGenerating}
            className="min-w-[200px]"
          >
            {isGenerating ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                Starting Generation...
              </>
            ) : (
              <>
                <Play className="w-5 h-5 mr-2" />
                Generate Synthetic Data
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ConfigureMultiTable;
