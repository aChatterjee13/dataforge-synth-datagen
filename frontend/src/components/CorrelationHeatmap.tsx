import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './Card';

interface CorrelationMatrix {
  [column: string]: { [column: string]: number };
}

interface CorrelationHeatmapProps {
  original: CorrelationMatrix;
  synthetic: CorrelationMatrix;
}

function getColor(value: number): string {
  // blue for positive, red for negative, white for zero
  const clamped = Math.max(-1, Math.min(1, value));
  if (clamped >= 0) {
    const intensity = Math.round(clamped * 220);
    return `rgb(${220 - intensity}, ${220 - intensity}, 255)`;
  } else {
    const intensity = Math.round(-clamped * 220);
    return `rgb(255, ${220 - intensity}, ${220 - intensity})`;
  }
}

function HeatmapGrid({
  matrix,
  columns,
  title,
}: {
  matrix: CorrelationMatrix;
  columns: string[];
  title: string;
}) {
  const [tooltip, setTooltip] = useState<{ col1: string; col2: string; value: number } | null>(null);

  const cellSize = columns.length > 10 ? 28 : columns.length > 6 ? 36 : 44;
  const labelWidth = 80;

  return (
    <div className="flex-1 min-w-0">
      <h3 className="text-sm font-semibold text-gray-700 mb-2 text-center">{title}</h3>
      <div className="overflow-auto">
        <div style={{ display: 'inline-block' }}>
          {/* Column labels (top) */}
          <div className="flex" style={{ marginLeft: labelWidth }}>
            {columns.map((col) => (
              <div
                key={col}
                style={{ width: cellSize, height: labelWidth }}
                className="flex items-end justify-center"
              >
                <span
                  className="text-[10px] text-gray-600 whitespace-nowrap origin-bottom-left"
                  style={{
                    transform: 'rotate(-45deg)',
                    transformOrigin: 'bottom left',
                    display: 'block',
                    marginBottom: 4,
                    marginLeft: cellSize / 2,
                  }}
                >
                  {col.length > 10 ? col.slice(0, 10) + '..' : col}
                </span>
              </div>
            ))}
          </div>

          {/* Rows */}
          {columns.map((row) => (
            <div key={row} className="flex items-center">
              {/* Row label */}
              <div
                style={{ width: labelWidth }}
                className="text-[10px] text-gray-600 text-right pr-2 truncate flex-shrink-0"
                title={row}
              >
                {row.length > 12 ? row.slice(0, 12) + '..' : row}
              </div>

              {/* Cells */}
              {columns.map((col) => {
                const value = matrix[row]?.[col] ?? 0;
                return (
                  <div
                    key={col}
                    style={{
                      width: cellSize,
                      height: cellSize,
                      backgroundColor: getColor(value),
                    }}
                    className="border border-gray-100 cursor-pointer relative"
                    onMouseEnter={() => setTooltip({ col1: row, col2: col, value })}
                    onMouseLeave={() => setTooltip(null)}
                  >
                    {cellSize >= 36 && (
                      <span className="absolute inset-0 flex items-center justify-center text-[9px] text-gray-700 font-mono">
                        {value.toFixed(2)}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div className="mt-2 text-xs text-gray-600 text-center">
          <span className="font-medium">{tooltip.col1}</span>
          {' vs '}
          <span className="font-medium">{tooltip.col2}</span>
          {': '}
          <span className="font-bold">{tooltip.value.toFixed(4)}</span>
        </div>
      )}
    </div>
  );
}

function ColorScale() {
  const steps = 11;
  return (
    <div className="flex items-center justify-center gap-2 mt-4">
      <span className="text-xs text-gray-500">-1</span>
      <div className="flex">
        {Array.from({ length: steps }, (_, i) => {
          const value = -1 + (2 * i) / (steps - 1);
          return (
            <div
              key={i}
              style={{
                width: 20,
                height: 12,
                backgroundColor: getColor(value),
              }}
              className="border border-gray-200"
            />
          );
        })}
      </div>
      <span className="text-xs text-gray-500">+1</span>
    </div>
  );
}

export default function CorrelationHeatmap({ original, synthetic }: CorrelationHeatmapProps) {
  const columns = Object.keys(original);

  if (columns.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Correlation Heatmaps</CardTitle>
        <CardDescription>
          Side-by-side comparison of feature correlations (blue = positive, red = negative)
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col lg:flex-row gap-6">
          <HeatmapGrid matrix={original} columns={columns} title="Original" />
          <HeatmapGrid matrix={synthetic} columns={columns} title="Synthetic" />
        </div>
        <ColorScale />
      </CardContent>
    </Card>
  );
}
