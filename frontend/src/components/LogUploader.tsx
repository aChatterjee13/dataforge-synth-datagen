import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Terminal, Upload, X, CheckCircle } from 'lucide-react';
import { Button } from './Button';
import { uploadLogs } from '../services/api';
import { getApiErrorMessage } from '../lib/utils';
import type { LogUploadResponse } from '../types';

interface LogUploaderProps {
  onUploadSuccess: (jobId: string, formatInfo: any) => void;
  onUploadError: (error: string) => void;
}

const FORMAT_BADGE_COLORS: Record<string, string> = {
  apache: 'bg-red-100 text-red-800',
  nginx: 'bg-green-100 text-green-800',
  syslog: 'bg-blue-100 text-blue-800',
  json: 'bg-purple-100 text-purple-800',
  csv: 'bg-amber-100 text-amber-800',
  custom: 'bg-gray-100 text-gray-800',
};

export default function LogUploader({ onUploadSuccess, onUploadError }: LogUploaderProps) {
  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [detectedFormat, setDetectedFormat] = useState<string | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/plain': ['.log', '.txt'],
      'application/json': ['.json'],
      'text/csv': ['.csv'],
    },
    disabled: uploading,
    multiple: false,
  });

  const removeFile = () => {
    setFile(null);
    setDetectedFormat(null);
  };

  const handleUpload = async () => {
    if (!file) {
      onUploadError('Please select a log file');
      return;
    }

    setUploading(true);
    setUploadSuccess(false);

    try {
      const data: LogUploadResponse = await uploadLogs(file);
      setUploadSuccess(true);
      setDetectedFormat(data.format_info?.detected_format || null);

      setTimeout(() => {
        onUploadSuccess(data.job_id, data.format_info);
      }, 1000);
    } catch (err: unknown) {
      onUploadError(getApiErrorMessage(err));
    } finally {
      setUploading(false);
    }
  };

  const formatBadgeClass = detectedFormat
    ? FORMAT_BADGE_COLORS[detectedFormat.toLowerCase()] || FORMAT_BADGE_COLORS.custom
    : '';

  return (
    <div>
      {/* Drop Zone */}
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors mb-4
          ${isDragActive ? 'border-emerald-500 bg-emerald-50' : 'border-gray-300 hover:border-gray-400'}
          ${uploading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />

        <div className="flex flex-col items-center">
          {uploadSuccess ? (
            <>
              <CheckCircle className="h-12 w-12 text-green-600 mb-4" />
              <p className="font-medium text-green-700">Upload Successful!</p>
              {detectedFormat && (
                <span className={`inline-block mt-2 px-3 py-1 rounded-full text-xs font-medium ${formatBadgeClass}`}>
                  Detected: {detectedFormat}
                </span>
              )}
              <p className="text-sm text-gray-600 mt-2">Analyzing log format...</p>
            </>
          ) : (
            <>
              <Upload className="h-12 w-12 text-gray-400 mb-4" />
              <p className="text-gray-700 font-medium mb-2">
                {isDragActive ? 'Drop your log file here' : 'Drag & drop a log file here'}
              </p>
              <p className="text-gray-500 text-sm mb-4">or</p>
              <Button type="button">Browse Files</Button>
              <p className="text-gray-400 text-xs mt-4">Supported: .log, .txt, .json, .csv</p>
            </>
          )}
        </div>
      </div>

      {/* Selected File */}
      {file && !uploadSuccess && (
        <div className="mb-4">
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200">
            <div className="flex items-center">
              <Terminal className="h-5 w-5 text-emerald-600 mr-3" />
              <div>
                <p className="font-medium text-sm text-gray-900">{file.name}</p>
                <p className="text-xs text-gray-500">
                  {file.size < 1024
                    ? `${file.size} B`
                    : file.size < 1024 * 1024
                    ? `${(file.size / 1024).toFixed(1)} KB`
                    : `${(file.size / 1024 / 1024).toFixed(2)} MB`}
                </p>
              </div>
            </div>
            <button
              onClick={removeFile}
              disabled={uploading}
              className="text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Upload Button */}
          <div className="mt-4">
            <Button
              onClick={handleUpload}
              disabled={uploading}
              className="w-full"
            >
              {uploading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                  Uploading...
                </>
              ) : (
                'Upload Log File'
              )}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
