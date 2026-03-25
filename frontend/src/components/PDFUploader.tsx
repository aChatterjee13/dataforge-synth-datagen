import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { FileText, Upload, X, CheckCircle } from 'lucide-react';
import { Button } from './Button';
import { uploadPDFs } from '../services/api';
import { getApiErrorMessage } from '../lib/utils';
import type { PDFInfo } from '../types';

interface PDFUploaderProps {
  onUploadSuccess: (jobId: string, pdfInfo: PDFInfo[]) => void;
  onUploadError: (error: string) => void;
}

export default function PDFUploader({ onUploadSuccess, onUploadError }: PDFUploaderProps) {
  const [uploading, setUploading] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles(prev => [...prev, ...acceptedFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    disabled: uploading,
    multiple: true
  });

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      onUploadError('Please select at least one PDF file');
      return;
    }

    setUploading(true);
    setUploadSuccess(false);

    try {
      const data = await uploadPDFs(files);
      setUploadSuccess(true);

      // Notify parent component
      setTimeout(() => {
        onUploadSuccess(data.job_id, data.pdf_info || []);
      }, 1000);

    } catch (err: unknown) {
      onUploadError(getApiErrorMessage(err));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      {/* Drop Zone */}
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors mb-4
          ${isDragActive ? 'border-purple-500 bg-purple-50' : 'border-gray-300 hover:border-gray-400'}
          ${uploading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />

        <div className="flex flex-col items-center">
          {uploadSuccess ? (
            <>
              <CheckCircle className="h-12 w-12 text-green-600 mb-4" />
              <p className="font-medium text-green-700">Upload Successful!</p>
              <p className="text-sm text-gray-600 mt-2">Processing PDFs...</p>
            </>
          ) : (
            <>
              <Upload className="h-12 w-12 text-gray-400 mb-4" />
              <p className="text-gray-700 font-medium mb-2">
                {isDragActive ? 'Drop PDFs here' : 'Drag & drop PDF files here'}
              </p>
              <p className="text-gray-500 text-sm mb-4">or</p>
              <Button type="button">Browse PDFs</Button>
              <p className="text-gray-400 text-xs mt-4">Supported format: PDF only</p>
            </>
          )}
        </div>
      </div>

      {/* Selected Files */}
      {files.length > 0 && !uploadSuccess && (
        <div className="mb-4">
          <h3 className="font-medium mb-2 text-gray-900">
            Selected Files ({files.length})
          </h3>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {files.map((file, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200"
              >
                <div className="flex items-center">
                  <FileText className="h-5 w-5 text-purple-600 mr-3" />
                  <div>
                    <p className="font-medium text-sm text-gray-900">{file.name}</p>
                    <p className="text-xs text-gray-500">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => removeFile(index)}
                  disabled={uploading}
                  className="text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            ))}
          </div>

          {/* Upload Button */}
          <div className="mt-4">
            <Button
              onClick={handleUpload}
              disabled={uploading || files.length === 0}
              className="w-full"
            >
              {uploading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                  Uploading {files.length} PDF(s)...
                </>
              ) : (
                <>Upload {files.length} PDF{files.length > 1 ? 's' : ''}</>
              )}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
