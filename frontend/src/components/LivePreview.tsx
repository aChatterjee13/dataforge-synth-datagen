import React, { useState, useEffect, useRef } from 'react';
import { getPreview } from '../services/api';
import type { PreviewData } from '../types';

interface LivePreviewProps {
  jobId: string;
  isGenerating: boolean;
}

const LivePreview: React.FC<LivePreviewProps> = ({ jobId, isGenerating }) => {
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const fetchPreview = async () => {
      try {
        const data = await getPreview(jobId, 20);
        setPreviewData(data);
        setError(null);
      } catch {
        // Silently handle errors during polling; preview may not be available yet
      }
    };

    if (isGenerating) {
      // Fetch immediately, then poll every 3 seconds
      fetchPreview();
      intervalRef.current = setInterval(fetchPreview, 3000);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [jobId, isGenerating]);

  // Also do a final fetch when generation completes
  useEffect(() => {
    if (!isGenerating && previewData && !previewData.is_complete) {
      const fetchFinal = async () => {
        try {
          const data = await getPreview(jobId, 20);
          setPreviewData(data);
        } catch {
          // Ignore errors on final fetch
        }
      };
      fetchFinal();
    }
  }, [isGenerating, jobId, previewData]);

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-sm text-red-600">{error}</p>
      </div>
    );
  }

  if (!previewData || previewData.rows_generated === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-8 text-center">
        <div className="flex flex-col items-center gap-3">
          <div className="flex space-x-1">
            <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
          <p className="text-gray-500 text-sm">Waiting for data...</p>
        </div>
      </div>
    );
  }

  const { rows_generated, total_requested, sample_data } = previewData;
  const progressPercent = total_requested > 0
    ? Math.min(100, Math.round((rows_generated / total_requested) * 100))
    : 0;

  const columnNames = sample_data.length > 0 ? Object.keys(sample_data[0]) : [];

  return (
    <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
      {/* Progress Header */}
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-gray-700">Live Preview</h3>
          <span className="text-sm text-gray-500">
            {rows_generated.toLocaleString()} / {total_requested.toLocaleString()} rows
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <p className="text-xs text-gray-400 mt-1">{progressPercent}% complete</p>
      </div>

      {/* Data Table */}
      {sample_data.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50">
                {columnNames.map((col) => (
                  <th
                    key={col}
                    className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wide whitespace-nowrap border-b border-gray-100"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sample_data.map((row, rowIndex) => (
                <tr
                  key={rowIndex}
                  className={rowIndex % 2 === 0 ? 'bg-white' : 'bg-gray-50'}
                >
                  {columnNames.map((col) => (
                    <td
                      key={col}
                      className="px-4 py-2 text-gray-700 whitespace-nowrap border-b border-gray-50 max-w-[200px] truncate"
                      title={String(row[col] ?? '')}
                    >
                      {row[col] != null ? String(row[col]) : ''}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default LivePreview;
