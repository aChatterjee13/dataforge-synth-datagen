import React from "react";

interface DataPreviewTableProps {
  data: Record<string, unknown>[];
  maxRows?: number;
}

function formatCellValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "-";
  }
  if (typeof value === "number") {
    return value.toLocaleString();
  }
  const str = String(value);
  if (str.length > 50) {
    return str.slice(0, 50) + "\u2026";
  }
  return str;
}

const DataPreviewTable: React.FC<DataPreviewTableProps> = ({
  data,
  maxRows = 10,
}) => {
  if (!data || data.length === 0) {
    return (
      <p className="text-sm text-gray-500 italic py-4">
        No data available to preview.
      </p>
    );
  }

  const columns = Object.keys(data[0]);
  const rows = data.slice(0, maxRows);

  return (
    <div className="overflow-x-auto rounded-md border border-gray-200">
      <table className="min-w-full text-sm">
        <thead className="sticky top-0 bg-gray-100 z-10">
          <tr>
            {columns.map((col) => (
              <th
                key={col}
                className="border border-gray-200 px-4 py-2 text-left font-semibold text-gray-700 whitespace-nowrap"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr
              key={rowIndex}
              className={rowIndex % 2 === 0 ? "bg-white" : "bg-gray-50"}
            >
              {columns.map((col) => (
                <td
                  key={col}
                  className="border border-gray-200 px-4 py-2 text-gray-600 whitespace-nowrap"
                  title={
                    row[col] !== null && row[col] !== undefined
                      ? String(row[col])
                      : undefined
                  }
                >
                  {formatCellValue(row[col])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default DataPreviewTable;
