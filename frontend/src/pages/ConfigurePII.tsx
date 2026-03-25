import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ShieldCheck, ShieldAlert, ArrowRight, Plus, X } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/Card';
import { Button } from '../components/Button';
import { generatePIIMask } from '../services/api';
import { getApiErrorMessage } from '../lib/utils';
import type { PIIColumnDetection } from '../types';

type MaskingStrategy = 'synthetic' | 'hash' | 'redact' | 'generalize';

interface ColumnStrategy {
  column_name: string;
  strategy: MaskingStrategy;
  selected: boolean;
}

export default function ConfigurePII() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const [piiColumns, setPiiColumns] = useState<PIIColumnDetection[]>([]);
  const [nonPiiColumns, setNonPiiColumns] = useState<string[]>([]);
  const [strategies, setStrategies] = useState<ColumnStrategy[]>([]);
  const [addedNonPiiColumns, setAddedNonPiiColumns] = useState<ColumnStrategy[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const stored = sessionStorage.getItem(`pii_detection_${jobId}`);
    if (stored) {
      try {
        const data = JSON.parse(stored);
        const detected: PIIColumnDetection[] = data.detected_pii_columns || [];
        const nonPii: string[] = data.non_pii_columns || [];

        setPiiColumns(detected);
        setNonPiiColumns(nonPii);

        // Initialize strategies: direct PII pre-checked, indirect PII unchecked
        setStrategies(
          detected.map((col) => ({
            column_name: col.column_name,
            strategy: (col.suggested_strategy as MaskingStrategy) || 'synthetic',
            selected: (col.pii_category || 'direct') === 'direct',
          }))
        );
      } catch (err) {
        console.error('Failed to parse PII detection data:', err);
      }
    }
  }, [jobId]);

  const updateStrategy = (columnName: string, strategy: MaskingStrategy) => {
    setStrategies((prev) =>
      prev.map((s) =>
        s.column_name === columnName ? { ...s, strategy } : s
      )
    );
    setAddedNonPiiColumns((prev) =>
      prev.map((s) =>
        s.column_name === columnName ? { ...s, strategy } : s
      )
    );
  };

  const toggleColumn = (columnName: string) => {
    setStrategies((prev) =>
      prev.map((s) =>
        s.column_name === columnName ? { ...s, selected: !s.selected } : s
      )
    );
    setAddedNonPiiColumns((prev) =>
      prev.map((s) =>
        s.column_name === columnName ? { ...s, selected: !s.selected } : s
      )
    );
  };

  const selectAll = (category?: 'direct' | 'indirect') => {
    setStrategies((prev) =>
      prev.map((s) => {
        if (!category) return { ...s, selected: true };
        const col = piiColumns.find((c) => c.column_name === s.column_name);
        if (col && (col.pii_category || 'direct') === category) {
          return { ...s, selected: true };
        }
        return s;
      })
    );
  };

  const deselectAll = (category?: 'direct' | 'indirect') => {
    setStrategies((prev) =>
      prev.map((s) => {
        if (!category) return { ...s, selected: false };
        const col = piiColumns.find((c) => c.column_name === s.column_name);
        if (col && (col.pii_category || 'direct') === category) {
          return { ...s, selected: false };
        }
        return s;
      })
    );
  };

  const addNonPiiColumn = (columnName: string) => {
    if (addedNonPiiColumns.some((c) => c.column_name === columnName)) return;
    setAddedNonPiiColumns((prev) => [
      ...prev,
      { column_name: columnName, strategy: 'redact', selected: true },
    ]);
    setNonPiiColumns((prev) => prev.filter((c) => c !== columnName));
  };

  const removeAddedColumn = (columnName: string) => {
    setAddedNonPiiColumns((prev) => prev.filter((c) => c.column_name !== columnName));
    setNonPiiColumns((prev) => [...prev, columnName]);
  };

  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 0.9) {
      return 'bg-green-100 text-green-800';
    } else if (confidence >= 0.7) {
      return 'bg-yellow-100 text-yellow-800';
    }
    return 'bg-red-100 text-red-800';
  };

  const getCategoryBadge = (category: string) => {
    if (category === 'direct') {
      return 'bg-red-100 text-red-800 border border-red-200';
    }
    return 'bg-amber-100 text-amber-800 border border-amber-200';
  };

  const selectedCount =
    strategies.filter((s) => s.selected).length +
    addedNonPiiColumns.filter((s) => s.selected).length;

  const directColumns = piiColumns.filter((c) => (c.pii_category || 'direct') === 'direct');
  const indirectColumns = piiColumns.filter((c) => (c.pii_category || 'direct') === 'indirect');

  const handleStartMasking = async () => {
    if (!jobId) return;

    setSubmitting(true);
    setError(null);

    try {
      // Only send selected columns' strategies
      const columnStrategies: Record<string, string> = {};
      strategies.forEach((s) => {
        if (s.selected) {
          columnStrategies[s.column_name] = s.strategy;
        }
      });
      addedNonPiiColumns.forEach((s) => {
        if (s.selected) {
          columnStrategies[s.column_name] = s.strategy;
        }
      });

      await generatePIIMask(jobId, {
        pii_column_strategies: columnStrategies,
      });

      navigate(`/generate/${jobId}`);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err));
      setSubmitting(false);
    }
  };

  const renderColumnRow = (
    col: PIIColumnDetection | null,
    strat: ColumnStrategy,
    isAdded: boolean = false
  ) => {
    const category = col ? (col.pii_category || 'direct') : 'custom';

    return (
      <tr
        key={strat.column_name}
        className={`border-b border-gray-100 hover:bg-gray-50 ${!strat.selected ? 'opacity-50' : ''}`}
      >
        {/* Checkbox */}
        <td className="py-3 px-4">
          <input
            type="checkbox"
            checked={strat.selected}
            onChange={() => isAdded ? toggleColumn(strat.column_name) : toggleColumn(strat.column_name)}
            className="h-4 w-4 text-emerald-600 border-gray-300 rounded focus:ring-emerald-500 cursor-pointer"
          />
        </td>
        {/* Column Name */}
        <td className="py-3 px-4 font-mono font-medium text-gray-900">
          <div className="flex items-center gap-2">
            {strat.column_name}
            {isAdded && (
              <button
                onClick={() => removeAddedColumn(strat.column_name)}
                className="text-gray-400 hover:text-red-500"
                title="Remove from masking"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </td>
        {/* PII Type */}
        <td className="py-3 px-4">
          <span className="px-2 py-0.5 bg-purple-100 text-purple-800 rounded text-xs font-medium">
            {col ? col.pii_type : 'custom'}
          </span>
        </td>
        {/* Category */}
        <td className="py-3 px-4">
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${getCategoryBadge(category)}`}>
            {category === 'direct' ? 'Direct' : category === 'indirect' ? 'Indirect' : 'Manual'}
          </span>
        </td>
        {/* Confidence */}
        <td className="py-3 px-4">
          {col ? (
            <span
              className={`px-2 py-0.5 rounded text-xs font-medium ${getConfidenceBadge(col.confidence)}`}
            >
              {(col.confidence * 100).toFixed(0)}%
            </span>
          ) : (
            <span className="text-gray-400 text-xs">--</span>
          )}
        </td>
        {/* Sample Values */}
        <td className="py-3 px-4">
          <div className="flex flex-wrap gap-1">
            {col?.sample_values?.slice(0, 2).map((val, i) => (
              <span
                key={i}
                className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs font-mono truncate max-w-[120px]"
                title={val}
              >
                {val}
              </span>
            )) || <span className="text-gray-400 text-xs">--</span>}
          </div>
        </td>
        {/* Strategy */}
        <td className="py-3 px-4">
          <select
            value={strat.strategy}
            onChange={(e) =>
              updateStrategy(strat.column_name, e.target.value as MaskingStrategy)
            }
            disabled={!strat.selected}
            className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent disabled:bg-gray-100 disabled:text-gray-400"
          >
            <option value="synthetic">Synthetic</option>
            <option value="hash">Hash</option>
            <option value="redact">Redact</option>
            <option value="generalize">Generalize</option>
          </select>
        </td>
      </tr>
    );
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="mb-8">
        <Button
          variant="outline"
          onClick={() => navigate('/upload')}
          className="mb-4"
        >
          &larr; Back to Upload
        </Button>
        <h1 className="text-3xl font-bold mb-2">Configure PII Masking</h1>
        <p className="text-gray-600">
          Review detected PII columns, select which ones to mask, and choose a strategy for each
        </p>
      </div>

      {/* Detected PII Columns */}
      {piiColumns.length > 0 ? (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <div className="flex items-center">
                <ShieldCheck className="h-5 w-5 mr-2 text-emerald-600" />
                Detected PII Columns ({piiColumns.length})
                {directColumns.length > 0 && (
                  <span className="ml-3 px-2 py-0.5 bg-red-100 text-red-700 rounded text-xs font-medium">
                    {directColumns.length} Direct
                  </span>
                )}
                {indirectColumns.length > 0 && (
                  <span className="ml-2 px-2 py-0.5 bg-amber-100 text-amber-700 rounded text-xs font-medium">
                    {indirectColumns.length} Indirect
                  </span>
                )}
              </div>
              <div className="flex gap-2 text-xs">
                <button
                  onClick={() => selectAll()}
                  className="px-2 py-1 text-emerald-700 hover:bg-emerald-50 rounded"
                >
                  Select All
                </button>
                <button
                  onClick={() => deselectAll()}
                  className="px-2 py-1 text-gray-500 hover:bg-gray-100 rounded"
                >
                  Deselect All
                </button>
                {indirectColumns.length > 0 && (
                  <button
                    onClick={() => selectAll('indirect')}
                    className="px-2 py-1 text-amber-700 hover:bg-amber-50 rounded"
                  >
                    + Indirect
                  </button>
                )}
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-700 w-10">Mask</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Column</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">PII Type</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Category</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Confidence</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Samples</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Strategy</th>
                  </tr>
                </thead>
                <tbody>
                  {/* Direct PII first */}
                  {directColumns.length > 0 && (
                    <tr>
                      <td colSpan={7} className="pt-3 pb-1 px-4">
                        <span className="text-xs font-semibold text-red-700 uppercase tracking-wide">
                          Direct PII -- Uniquely Identifies Individuals
                        </span>
                      </td>
                    </tr>
                  )}
                  {directColumns.map((col) => {
                    const strat = strategies.find((s) => s.column_name === col.column_name);
                    if (!strat) return null;
                    return renderColumnRow(col, strat);
                  })}

                  {/* Indirect PII */}
                  {indirectColumns.length > 0 && (
                    <tr>
                      <td colSpan={7} className="pt-5 pb-1 px-4">
                        <div className="flex items-center gap-2">
                          <ShieldAlert className="h-4 w-4 text-amber-600" />
                          <span className="text-xs font-semibold text-amber-700 uppercase tracking-wide">
                            Indirect PII -- Quasi-identifiers (re-identify when combined)
                          </span>
                        </div>
                      </td>
                    </tr>
                  )}
                  {indirectColumns.map((col) => {
                    const strat = strategies.find((s) => s.column_name === col.column_name);
                    if (!strat) return null;
                    return renderColumnRow(col, strat);
                  })}

                  {/* Manually added non-PII columns */}
                  {addedNonPiiColumns.length > 0 && (
                    <tr>
                      <td colSpan={7} className="pt-5 pb-1 px-4">
                        <span className="text-xs font-semibold text-blue-700 uppercase tracking-wide">
                          Manually Added Columns
                        </span>
                      </td>
                    </tr>
                  )}
                  {addedNonPiiColumns.map((strat) =>
                    renderColumnRow(null, strat, true)
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="mb-6">
          <CardContent className="py-8">
            <div className="text-center text-gray-600">
              <p className="font-medium">No PII columns detected</p>
              <p className="text-sm mt-1">Upload a dataset with PII data to configure masking</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Non-PII Columns (with add-to-masking capability) */}
      {nonPiiColumns.length > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-lg text-gray-500">
              Non-PII Columns ({nonPiiColumns.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {nonPiiColumns.map((col) => (
                <button
                  key={col}
                  onClick={() => addNonPiiColumn(col)}
                  className="group px-3 py-1.5 bg-gray-100 hover:bg-blue-50 hover:border-blue-300 text-gray-600 hover:text-blue-700 rounded-md text-sm font-mono border border-transparent transition-colors flex items-center gap-1.5"
                  title="Click to add to masking list"
                >
                  <Plus className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                  {col}
                </button>
              ))}
            </div>
            <p className="text-xs text-gray-400 mt-3">
              Click any column to add it to the masking list
            </p>
          </CardContent>
        </Card>
      )}

      {/* Info Box */}
      <Card className="mb-6 bg-emerald-50 border-emerald-200">
        <CardContent className="pt-6">
          <div className="flex items-start">
            <ShieldCheck className="h-5 w-5 text-emerald-700 mr-3 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-emerald-900">
              <p className="font-semibold mb-2">Masking Strategies</p>
              <ul className="space-y-1 text-xs">
                <li><strong>Synthetic</strong> -- Replaces PII with realistic fake data that preserves statistical properties</li>
                <li><strong>Hash</strong> -- Applies format-preserving hashing to anonymize values while maintaining referential integrity</li>
                <li><strong>Redact</strong> -- Completely removes PII values and replaces with placeholders</li>
                <li><strong>Generalize</strong> -- Reduces specificity (e.g., exact age becomes age range, salary becomes bracket)</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800 text-sm">{error}</p>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-4">
        <Button
          variant="outline"
          onClick={() => navigate('/upload')}
          className="flex-1"
        >
          Cancel
        </Button>
        <Button
          onClick={handleStartMasking}
          disabled={submitting || selectedCount === 0}
          className="flex-1 bg-emerald-600 hover:bg-emerald-700"
        >
          {submitting ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
              Starting...
            </>
          ) : (
            <>
              Mask {selectedCount} Column{selectedCount !== 1 ? 's' : ''}
              <ArrowRight className="h-4 w-4 ml-2" />
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
