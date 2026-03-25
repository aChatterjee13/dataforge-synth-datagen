import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { GitBranch, Table, Columns, Key, ArrowDownUp } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/Card';
import { Button } from '../components/Button';
import ErrorBanner from '../components/ErrorBanner';
import { generateCDC } from '../services/api';
import { getApiErrorMessage } from '../lib/utils';

const OUTPUT_FORMATS = [
  { value: 'debezium', label: 'Debezium JSON' },
  { value: 'sql', label: 'SQL Statements' },
  { value: 'csv', label: 'CSV' },
];

interface CDCSchemaInfo {
  total_tables: number;
  total_columns: number;
  total_foreign_keys: number;
  table_names?: string[];
  dependency_order?: string[];
}

export default function ConfigureCDC() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  // Load schema info from sessionStorage
  const schemaRaw = sessionStorage.getItem(`cdc_schema_${jobId}`);
  const schema: CDCSchemaInfo | null = schemaRaw ? JSON.parse(schemaRaw) : null;

  const [eventCount, setEventCount] = useState(500);
  const [timeRangeHours, setTimeRangeHours] = useState(24);
  const [insertRatio, setInsertRatio] = useState(0.5);
  const [updateRatio, setUpdateRatio] = useState(0.3);
  const [deleteRatio, setDeleteRatio] = useState(0.2);
  const [outputFormat, setOutputFormat] = useState('debezium');
  const [error, setError] = useState<string | null>(null);

  const totalRatio = insertRatio + updateRatio + deleteRatio;

  const formatPercent = (value: number): string => {
    if (totalRatio === 0) return '0%';
    return `${((value / totalRatio) * 100).toFixed(1)}%`;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const config = {
        model_type: 'cdc_gen',
        num_rows: 0,
        epochs: 0,
        batch_size: 0,
        data_type: 'cdc_testing',
        cdc_event_count: eventCount,
        cdc_time_range_hours: timeRangeHours,
        cdc_insert_ratio: insertRatio,
        cdc_update_ratio: updateRatio,
        cdc_delete_ratio: deleteRatio,
        cdc_output_format: outputFormat,
      };

      await generateCDC(jobId!, config);
      navigate(`/generate/${jobId}`);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err));
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}
      <div className="mb-8">
        <Button variant="outline" onClick={() => navigate('/')} className="mb-4">
          ← Back to Upload
        </Button>
        <h1 className="text-3xl font-bold mb-2">Configure CDC Event Generation</h1>
        <p className="text-gray-600">Generate Change Data Capture events from your database schema</p>
      </div>

      {/* Schema Summary */}
      {schema && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center">
              <GitBranch className="h-5 w-5 mr-2 text-amber-600" />
              Schema Summary
            </CardTitle>
            <CardDescription>Parsed schema information</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="flex items-center gap-2">
                <Table className="h-4 w-4 text-gray-500" />
                <span className="text-sm">
                  <span className="font-semibold">{schema.total_tables}</span> Tables
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Columns className="h-4 w-4 text-gray-500" />
                <span className="text-sm">
                  <span className="font-semibold">{schema.total_columns}</span> Columns
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Key className="h-4 w-4 text-gray-500" />
                <span className="text-sm">
                  <span className="font-semibold">{schema.total_foreign_keys}</span> Foreign Keys
                </span>
              </div>
            </div>

            {schema.table_names && schema.table_names.length > 0 && (
              <div className="mb-3">
                <div className="text-xs font-medium text-gray-700 mb-1">Tables:</div>
                <div className="flex flex-wrap gap-2">
                  {schema.table_names.map(name => (
                    <span
                      key={name}
                      className="px-2 py-1 bg-gray-100 border rounded text-xs font-mono"
                    >
                      {name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {schema.dependency_order && schema.dependency_order.length > 1 && (
              <div>
                <div className="text-xs font-medium text-gray-700 mb-1">Dependency Order:</div>
                <div className="flex flex-wrap items-center gap-2">
                  {schema.dependency_order.map((table, i) => (
                    <div key={table} className="flex items-center">
                      <div className="px-2 py-1 bg-amber-100 border border-amber-300 rounded text-xs font-mono font-medium">
                        {table}
                      </div>
                      {i < schema.dependency_order!.length - 1 && (
                        <span className="mx-1 text-gray-400 font-bold">→</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Event Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <GitBranch className="h-5 w-5 mr-2 text-amber-600" />
              Event Settings
            </CardTitle>
            <CardDescription>Configure the number and time range of CDC events</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Event Count
              </label>
              <input
                type="number"
                min="50"
                max="50000"
                value={eventCount}
                onChange={e => setEventCount(parseInt(e.target.value) || 500)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
              />
              <p className="text-xs text-gray-500 mt-1">
                Total number of CDC events to generate (50 - 50,000)
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Time Range (hours)
              </label>
              <input
                type="number"
                min="1"
                max="8760"
                value={timeRangeHours}
                onChange={e => setTimeRangeHours(parseInt(e.target.value) || 24)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
              />
              <p className="text-xs text-gray-500 mt-1">
                Time window for generated events (1 - 8,760 hours / 1 year)
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Operation Ratios */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <ArrowDownUp className="h-5 w-5 mr-2 text-amber-600" />
              Operation Ratios
            </CardTitle>
            <CardDescription>Adjust the proportion of INSERT, UPDATE, and DELETE events</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-gray-700">INSERT</label>
                <span className="text-sm font-semibold text-green-600">
                  {insertRatio.toFixed(2)} ({formatPercent(insertRatio)})
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={insertRatio}
                onChange={e => setInsertRatio(parseFloat(e.target.value))}
                className="w-full accent-green-600"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-gray-700">UPDATE</label>
                <span className="text-sm font-semibold text-blue-600">
                  {updateRatio.toFixed(2)} ({formatPercent(updateRatio)})
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={updateRatio}
                onChange={e => setUpdateRatio(parseFloat(e.target.value))}
                className="w-full accent-blue-600"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-gray-700">DELETE</label>
                <span className="text-sm font-semibold text-red-600">
                  {deleteRatio.toFixed(2)} ({formatPercent(deleteRatio)})
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={deleteRatio}
                onChange={e => setDeleteRatio(parseFloat(e.target.value))}
                className="w-full accent-red-600"
              />
            </div>

            {totalRatio === 0 && (
              <p className="text-xs text-red-600">At least one ratio must be greater than zero.</p>
            )}
          </CardContent>
        </Card>

        {/* Output Format */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <GitBranch className="h-5 w-5 mr-2 text-amber-600" />
              Output Format
            </CardTitle>
          </CardHeader>
          <CardContent>
            <select
              value={outputFormat}
              onChange={e => setOutputFormat(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
            >
              {OUTPUT_FORMATS.map(f => (
                <option key={f.value} value={f.value}>{f.label}</option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Format for the generated CDC event stream
            </p>
          </CardContent>
        </Card>

        {/* Info */}
        <Card className="bg-amber-50 border-amber-200">
          <CardContent className="pt-6">
            <div className="flex items-start">
              <GitBranch className="h-5 w-5 text-amber-700 mr-3 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-amber-900">
                <p className="font-semibold mb-2">How CDC Event Generation Works</p>
                <ul className="space-y-1 text-xs">
                  <li>- Parses your schema to understand tables, columns, and relationships</li>
                  <li>- Generates realistic INSERT, UPDATE, and DELETE events in dependency order</li>
                  <li>- Maintains referential integrity across foreign key relationships</li>
                  <li>- Produces timestamped events suitable for CDC pipeline testing</li>
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
          <Button
            type="submit"
            className="flex-1 bg-amber-600 hover:bg-amber-700"
            disabled={totalRatio === 0}
          >
            Generate CDC Events
          </Button>
        </div>
      </form>
    </div>
  );
}
