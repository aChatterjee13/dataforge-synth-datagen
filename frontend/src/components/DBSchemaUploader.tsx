import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Database, Upload, CheckCircle } from 'lucide-react';
import { Button } from './Button';
import { uploadDBSchema } from '../services/api';
import { getApiErrorMessage } from '../lib/utils';

interface DBSchemaUploaderProps {
  onUploadSuccess: (jobId: string, schemaInfo: Record<string, unknown>) => void;
  onUploadError: (error: string) => void;
}

export default function DBSchemaUploader({ onUploadSuccess, onUploadError }: DBSchemaUploaderProps) {
  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/plain': ['.sql', '.ddl'],
      'application/json': ['.json'],
      'application/x-yaml': ['.yaml', '.yml'],
    },
    disabled: uploading,
    multiple: false,
  });

  const handleUpload = async () => {
    if (!file) {
      onUploadError('Please select a schema file');
      return;
    }

    setUploading(true);
    setUploadSuccess(false);

    try {
      const data = await uploadDBSchema(file);
      setUploadSuccess(true);

      setTimeout(() => {
        onUploadSuccess(data.job_id, data as unknown as Record<string, unknown>);
      }, 1000);
    } catch (err: unknown) {
      onUploadError(getApiErrorMessage(err));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors mb-4
          ${isDragActive ? 'border-amber-500 bg-amber-50' : 'border-gray-300 hover:border-gray-400'}
          ${uploading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center">
          {uploadSuccess ? (
            <>
              <CheckCircle className="h-12 w-12 text-green-600 mb-4" />
              <p className="font-medium text-green-700">Upload Successful!</p>
              <p className="text-sm text-gray-600 mt-2">Analyzing schema...</p>
            </>
          ) : (
            <>
              <Upload className="h-12 w-12 text-gray-400 mb-4" />
              <p className="text-gray-700 font-medium mb-2">
                {isDragActive ? 'Drop your schema here' : 'Drag & drop your DB schema here'}
              </p>
              <p className="text-gray-500 text-sm mb-4">or</p>
              <Button type="button">Browse Files</Button>
              <p className="text-gray-400 text-xs mt-4">Supported: SQL DDL, JSON, YAML</p>
            </>
          )}
        </div>
      </div>

      {file && !uploadSuccess && (
        <div className="mb-4">
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200">
            <div className="flex items-center">
              <Database className="h-5 w-5 text-amber-600 mr-3" />
              <div>
                <p className="font-medium text-sm text-gray-900">{file.name}</p>
                <p className="text-xs text-gray-500">{(file.size / 1024).toFixed(1)} KB</p>
              </div>
            </div>
          </div>
          <div className="mt-4">
            <Button onClick={handleUpload} disabled={uploading} className="w-full">
              {uploading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                  Uploading...
                </>
              ) : (
                'Upload Schema'
              )}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
