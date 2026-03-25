import React from 'react';
import { Plus, X, ArrowRight } from 'lucide-react';
import { Button } from './Button';
import type { TableRelationship } from '../types';

interface RelationshipBuilderProps {
  tables: Record<string, { rows: number; columns: number; column_types: Record<string, string> }>;
  relationships: TableRelationship[];
  onRelationshipsChange: (relationships: TableRelationship[]) => void;
}

const RelationshipBuilder: React.FC<RelationshipBuilderProps> = ({
  tables,
  relationships,
  onRelationshipsChange,
}) => {
  const tableNames = Object.keys(tables);

  const getColumnsForTable = (tableName: string): string[] => {
    if (!tableName || !tables[tableName]) return [];
    return Object.keys(tables[tableName].column_types);
  };

  const addRelationship = () => {
    onRelationshipsChange([
      ...relationships,
      {
        parent_table: '',
        parent_column: '',
        child_table: '',
        child_column: '',
      },
    ]);
  };

  const removeRelationship = (index: number) => {
    const updated = relationships.filter((_, i) => i !== index);
    onRelationshipsChange(updated);
  };

  const updateRelationship = (
    index: number,
    field: keyof TableRelationship,
    value: string
  ) => {
    const updated = relationships.map((rel, i) => {
      if (i !== index) return rel;

      const newRel = { ...rel, [field]: value };

      // Reset column selection when table changes
      if (field === 'parent_table') {
        newRel.parent_column = '';
      }
      if (field === 'child_table') {
        newRel.child_column = '';
      }

      return newRel;
    });

    onRelationshipsChange(updated);
  };

  return (
    <div className="space-y-4">
      {relationships.length === 0 && (
        <div className="text-center py-8 border-2 border-dashed border-gray-200 rounded-lg">
          <p className="text-gray-500 text-sm">
            No relationships defined yet. Add a relationship to link tables together.
          </p>
        </div>
      )}

      {relationships.map((rel, index) => {
        const parentColumns = getColumnsForTable(rel.parent_table);
        const childColumns = getColumnsForTable(rel.child_table);

        return (
          <div
            key={index}
            className="flex items-center gap-3 p-4 border rounded-lg bg-gray-50"
          >
            {/* Parent Table & Column */}
            <div className="flex-1 space-y-2">
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide">
                Parent Table
              </label>
              <select
                value={rel.parent_table}
                onChange={(e) => updateRelationship(index, 'parent_table', e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white"
              >
                <option value="">Select table...</option>
                {tableNames.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>

              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide">
                Parent Column
              </label>
              <select
                value={rel.parent_column}
                onChange={(e) => updateRelationship(index, 'parent_column', e.target.value)}
                disabled={!rel.parent_table}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white disabled:bg-gray-100 disabled:text-gray-400"
              >
                <option value="">Select column...</option>
                {parentColumns.map((col) => (
                  <option key={col} value={col}>
                    {col}
                  </option>
                ))}
              </select>
            </div>

            {/* Arrow Icon */}
            <div className="flex-shrink-0 pt-6">
              <ArrowRight className="w-6 h-6 text-blue-500" />
            </div>

            {/* Child Table & Column */}
            <div className="flex-1 space-y-2">
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide">
                Child Table
              </label>
              <select
                value={rel.child_table}
                onChange={(e) => updateRelationship(index, 'child_table', e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white"
              >
                <option value="">Select table...</option>
                {tableNames.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>

              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide">
                Child Column
              </label>
              <select
                value={rel.child_column}
                onChange={(e) => updateRelationship(index, 'child_column', e.target.value)}
                disabled={!rel.child_table}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white disabled:bg-gray-100 disabled:text-gray-400"
              >
                <option value="">Select column...</option>
                {childColumns.map((col) => (
                  <option key={col} value={col}>
                    {col}
                  </option>
                ))}
              </select>
            </div>

            {/* Remove Button */}
            <div className="flex-shrink-0 pt-6">
              <button
                type="button"
                onClick={() => removeRelationship(index)}
                className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-md transition-colors"
                title="Remove relationship"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
        );
      })}

      <Button variant="outline" size="sm" onClick={addRelationship}>
        <Plus className="w-4 h-4 mr-2" />
        Add Relationship
      </Button>
    </div>
  );
};

export default RelationshipBuilder;
