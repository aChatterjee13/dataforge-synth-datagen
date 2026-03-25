import React from 'react';
import { Plus, X, Info } from 'lucide-react';
import { Button } from './Button';
import type { GenerationCondition } from '../types';

interface ConditionBuilderProps {
  columns: string[];
  conditions: GenerationCondition[];
  onConditionsChange: (conditions: GenerationCondition[]) => void;
}

const OPERATOR_OPTIONS: { value: GenerationCondition['operator']; label: string }[] = [
  { value: 'eq', label: '=' },
  { value: 'ne', label: '!=' },
  { value: 'gt', label: '>' },
  { value: 'lt', label: '<' },
  { value: 'gte', label: '>=' },
  { value: 'lte', label: '<=' },
];

const ConditionBuilder: React.FC<ConditionBuilderProps> = ({
  columns,
  conditions,
  onConditionsChange,
}) => {
  const addCondition = () => {
    onConditionsChange([
      ...conditions,
      {
        column: '',
        operator: 'eq',
        value: '',
      },
    ]);
  };

  const removeCondition = (index: number) => {
    const updated = conditions.filter((_, i) => i !== index);
    onConditionsChange(updated);
  };

  const updateCondition = (
    index: number,
    field: keyof GenerationCondition,
    rawValue: string
  ) => {
    const updated = conditions.map((cond, i) => {
      if (i !== index) return cond;

      if (field === 'value') {
        // Attempt to parse as number; keep as string if not numeric
        const trimmed = rawValue.trim();
        const numericValue = Number(trimmed);
        const parsedValue =
          trimmed !== '' && !isNaN(numericValue) ? numericValue : rawValue;

        return { ...cond, value: parsedValue };
      }

      return { ...cond, [field]: rawValue };
    });

    onConditionsChange(updated);
  };

  return (
    <div className="space-y-4">
      {/* Info text */}
      <div className="flex items-start gap-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <Info className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
        <p className="text-sm text-blue-700">
          Conditions filter the generated rows. Only rows matching all specified conditions
          will be included in the final synthetic dataset.
        </p>
      </div>

      {conditions.length === 0 && (
        <div className="text-center py-6 border-2 border-dashed border-gray-200 rounded-lg">
          <p className="text-gray-500 text-sm">
            No conditions defined. Add a condition to filter the generated data.
          </p>
        </div>
      )}

      {conditions.map((cond, index) => (
        <div
          key={index}
          className="flex items-center gap-3 p-3 border rounded-lg bg-gray-50"
        >
          {/* Column Dropdown */}
          <div className="flex-1">
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Column
            </label>
            <select
              value={cond.column}
              onChange={(e) => updateCondition(index, 'column', e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white"
            >
              <option value="">Select column...</option>
              {columns.map((col) => (
                <option key={col} value={col}>
                  {col}
                </option>
              ))}
            </select>
          </div>

          {/* Operator Dropdown */}
          <div className="w-28">
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Operator
            </label>
            <select
              value={cond.operator}
              onChange={(e) => updateCondition(index, 'operator', e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white"
            >
              {OPERATOR_OPTIONS.map((op) => (
                <option key={op.value} value={op.value}>
                  {op.label}
                </option>
              ))}
            </select>
          </div>

          {/* Value Input */}
          <div className="flex-1">
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Value
            </label>
            <input
              type="text"
              value={String(cond.value)}
              onChange={(e) => updateCondition(index, 'value', e.target.value)}
              placeholder="Enter value..."
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Remove Button */}
          <div className="flex-shrink-0 pt-5">
            <button
              type="button"
              onClick={() => removeCondition(index)}
              className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-md transition-colors"
              title="Remove condition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
      ))}

      <Button variant="outline" size="sm" onClick={addCondition}>
        <Plus className="w-4 h-4 mr-2" />
        Add Condition
      </Button>
    </div>
  );
};

export default ConditionBuilder;
