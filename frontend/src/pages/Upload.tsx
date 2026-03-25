import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { Upload as UploadIcon, File, AlertCircle, History, ArrowLeftRight, Activity, Settings, ArrowRight } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/Card';
import { Button } from '../components/Button';
import DataTypeSelector from '../components/DataTypeSelector';
import DataPreviewTable from '../components/DataPreviewTable';
import PDFUploader from '../components/PDFUploader';
import APISpecUploader from '../components/APISpecUploader';
import DBSchemaUploader from '../components/DBSchemaUploader';
import LogUploader from '../components/LogUploader';
import GraphUploader from '../components/GraphUploader';
import { uploadDataset, uploadMultiTable, uploadPIIDataset, uploadCDCSchema } from '../services/api';
import { getApiErrorMessage } from '../lib/utils';
import type { UploadResponse, DataType, PDFInfo } from '../types';

export default function Upload() {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadData, setUploadData] = useState<UploadResponse | null>(null);
  const [dataType, setDataType] = useState<DataType>('structured');
  const [multiFiles, setMultiFiles] = useState<File[]>([]);
  const [multiUploading, setMultiUploading] = useState(false);
  const navigate = useNavigate();

  // Handler for PDF upload success
  const handlePDFUploadSuccess = (jobId: string, _pdfInfo: PDFInfo[]) => {
    navigate(`/configure-pdf/${jobId}`);
  };

  // Handler for API spec upload success
  const handleAPISpecUploadSuccess = (jobId: string) => {
    navigate(`/configure-api-test/${jobId}`);
  };

  // Handler for DB schema upload success
  const handleDBSchemaUploadSuccess = (jobId: string) => {
    navigate(`/configure-db-test/${jobId}`);
  };

  // Handler for upload errors
  const handleUploadError = (errorMsg: string) => {
    setError(errorMsg);
  };

  // Handler for PII upload
  const [piiUploading, setPiiUploading] = useState(false);
  const handlePIIUpload = async (acceptedFiles: globalThis.File[]) => {
    if (acceptedFiles.length === 0) return;
    setPiiUploading(true);
    setError(null);
    try {
      const response = await uploadPIIDataset(acceptedFiles[0]);
      sessionStorage.setItem(`pii_detection_${response.job_id}`, JSON.stringify(response));
      navigate(`/configure-pii/${response.job_id}`);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err));
    } finally {
      setPiiUploading(false);
    }
  };

  // Handler for Log upload success
  const handleLogUploadSuccess = (jobId: string, formatInfo: any) => {
    sessionStorage.setItem(`log_info_${jobId}`, JSON.stringify(formatInfo));
    navigate(`/configure-logs/${jobId}`);
  };

  // Handler for CDC schema upload
  const [cdcUploading, setCdcUploading] = useState(false);
  const handleCDCUpload = async (file: globalThis.File) => {
    setCdcUploading(true);
    setError(null);
    try {
      const response = await uploadCDCSchema(file);
      sessionStorage.setItem(`cdc_schema_${response.job_id}`, JSON.stringify(response.schema_info));
      navigate(`/configure-cdc/${response.job_id}`);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err));
    } finally {
      setCdcUploading(false);
    }
  };

  // Handler for Graph upload success
  const handleGraphUploadSuccess = (jobId: string, graphStats: any) => {
    sessionStorage.setItem(`graph_stats_${jobId}`, JSON.stringify(graphStats));
    navigate(`/configure-graph/${jobId}`);
  };

  // Handler for multi-table upload
  const handleMultiTableUpload = async () => {
    if (multiFiles.length < 2) {
      setError('Please select at least 2 CSV files for multi-table synthesis');
      return;
    }
    setMultiUploading(true);
    setError(null);
    try {
      const response = await uploadMultiTable(multiFiles);
      sessionStorage.setItem(`multi_table_${response.job_id}`, JSON.stringify(response));
      navigate(`/configure-multi/${response.job_id}`);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err));
    } finally {
      setMultiUploading(false);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: async (acceptedFiles) => {
      if (acceptedFiles.length === 0) return;

      const file = acceptedFiles[0];
      setUploading(true);
      setError(null);

      try {
        const response = await uploadDataset(file);
        setUploadData(response);

        if (response.potential_targets) {
          sessionStorage.setItem(
            `targets_${response.job_id}`,
            JSON.stringify(response.potential_targets)
          );
        }

        if (response.is_timeseries && response.timeseries_info) {
          sessionStorage.setItem(
            `timeseries_${response.job_id}`,
            JSON.stringify(response.timeseries_info)
          );
        }

        // Store column types for column config
        if (response.column_types) {
          sessionStorage.setItem(
            `column_types_${response.job_id}`,
            JSON.stringify(response.column_types)
          );
        }
      } catch (err: unknown) {
        setError(getApiErrorMessage(err));
      } finally {
        setUploading(false);
      }
    },
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls']
    },
    maxFiles: 1,
    disabled: uploading
  });

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="mb-8 text-center">
        <h1 className="text-4xl font-bold mb-2">DataForge</h1>
        <p className="text-gray-600">Generate Privacy-Safe Synthetic Data</p>
      </div>

      {/* Data Type Selector */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-center mb-6">Choose Data Type</h2>
        <DataTypeSelector
          selectedType={dataType}
          onTypeSelect={setDataType}
        />
      </div>

      {/* Conditional Upload based on data type */}
      {dataType === 'structured' && (
        <Card>
          <CardHeader>
            <CardTitle>Upload Dataset</CardTitle>
            <CardDescription>
              Upload your CSV or Excel file to get started with synthetic data generation
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div
              {...getRootProps()}
              className={`
                border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors
                ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
                ${uploading ? 'opacity-50 cursor-not-allowed' : ''}
              `}
            >
              <input {...getInputProps()} />
              {uploading ? (
                <div className="flex flex-col items-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4" />
                  <p className="text-gray-600">Uploading and analyzing...</p>
                </div>
              ) : uploadData ? (
                <div className="flex flex-col items-center text-green-600">
                  <File className="h-12 w-12 mb-4" />
                  <p className="font-medium">Upload successful!</p>
                  <p className="text-sm text-gray-600 mt-2">
                    {uploadData.rows.toLocaleString()} rows x {uploadData.columns} columns
                  </p>
                </div>
              ) : (
                <div className="flex flex-col items-center">
                  <UploadIcon className="h-12 w-12 text-gray-400 mb-4" />
                  <p className="text-gray-700 font-medium mb-2">
                    {isDragActive ? 'Drop your file here' : 'Drag & drop your file here'}
                  </p>
                  <p className="text-gray-500 text-sm mb-4">or</p>
                  <Button type="button">Browse Files</Button>
                  <p className="text-gray-400 text-xs mt-4">Supported formats: CSV, XLSX, XLS</p>
                </div>
              )}
            </div>

            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start">
                <AlertCircle className="h-5 w-5 text-red-600 mr-2 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-red-800 font-medium">Upload Failed</p>
                  <p className="text-red-600 text-sm">{error}</p>
                </div>
              </div>
            )}

            {uploadData && !error && (
              <div className="mt-6 space-y-4">
                <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                  <h3 className="font-medium text-green-900 mb-2">Dataset Information</h3>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">File:</span>
                      <span className="ml-2 font-medium">{uploadData.filename}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Rows:</span>
                      <span className="ml-2 font-medium">{uploadData.rows.toLocaleString()}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Columns:</span>
                      <span className="ml-2 font-medium">{uploadData.columns}</span>
                    </div>
                  </div>
                </div>

                {/* Data Preview (Feature 2) */}
                {uploadData.sample_data && uploadData.sample_data.length > 0 && (
                  <div>
                    <h3 className="font-medium text-gray-900 mb-2">Data Preview (First 10 Rows)</h3>
                    <DataPreviewTable data={uploadData.sample_data} />
                  </div>
                )}

                <Button
                  onClick={() => navigate(`/configure/${uploadData.job_id}`)}
                  className="w-full"
                  size="lg"
                >
                  Continue to Configure <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {dataType === 'unstructured' && (
        <Card>
          <CardHeader>
            <CardTitle>Upload PDFs</CardTitle>
            <CardDescription>
              Upload sample PDF files to generate synthetic documents with GPT-powered generation
            </CardDescription>
          </CardHeader>
          <CardContent>
            <PDFUploader
              onUploadSuccess={handlePDFUploadSuccess}
              onUploadError={handleUploadError}
            />
            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start">
                <AlertCircle className="h-5 w-5 text-red-600 mr-2 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-red-800 font-medium">Upload Failed</p>
                  <p className="text-red-600 text-sm">{error}</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {dataType === 'api_testing' && (
        <Card>
          <CardHeader>
            <CardTitle>Upload OpenAPI Spec</CardTitle>
            <CardDescription>
              Upload your OpenAPI/Swagger specification to generate comprehensive API test suites
            </CardDescription>
          </CardHeader>
          <CardContent>
            <APISpecUploader
              onUploadSuccess={handleAPISpecUploadSuccess}
              onUploadError={handleUploadError}
            />
            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start">
                <AlertCircle className="h-5 w-5 text-red-600 mr-2 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-red-800 font-medium">Upload Failed</p>
                  <p className="text-red-600 text-sm">{error}</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {dataType === 'data_testing' && (
        <Card>
          <CardHeader>
            <CardTitle>Upload Database Schema</CardTitle>
            <CardDescription>
              Upload your database schema (SQL DDL, JSON, or YAML) to generate test data
            </CardDescription>
          </CardHeader>
          <CardContent>
            <DBSchemaUploader
              onUploadSuccess={handleDBSchemaUploadSuccess}
              onUploadError={handleUploadError}
            />
            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start">
                <AlertCircle className="h-5 w-5 text-red-600 mr-2 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-red-800 font-medium">Upload Failed</p>
                  <p className="text-red-600 text-sm">{error}</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {dataType === ('multi_table' as DataType) && (
        <Card>
          <CardHeader>
            <CardTitle>Upload Multiple Tables</CardTitle>
            <CardDescription>
              Upload multiple related CSV files for multi-table synthetic data generation with referential integrity
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
                <input
                  type="file"
                  multiple
                  accept=".csv"
                  onChange={(e) => {
                    if (e.target.files) {
                      setMultiFiles(Array.from(e.target.files));
                      setError(null);
                    }
                  }}
                  className="hidden"
                  id="multi-file-input"
                />
                <label htmlFor="multi-file-input" className="cursor-pointer">
                  <UploadIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-700 font-medium mb-2">Select CSV files</p>
                  <p className="text-gray-500 text-sm">Upload 2 or more related CSV tables</p>
                </label>
              </div>

              {multiFiles.length > 0 && (
                <div className="space-y-2">
                  <h3 className="font-medium text-gray-900">Selected Files ({multiFiles.length})</h3>
                  {multiFiles.map((f, i) => (
                    <div key={i} className="flex items-center gap-2 p-2 bg-gray-50 rounded">
                      <File className="h-4 w-4 text-gray-500" />
                      <span className="text-sm text-gray-700">{f.name}</span>
                      <span className="text-xs text-gray-400">({(f.size / 1024).toFixed(1)} KB)</span>
                    </div>
                  ))}
                  <Button
                    onClick={handleMultiTableUpload}
                    disabled={multiUploading}
                    className="w-full"
                    size="lg"
                  >
                    {multiUploading ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                        Uploading...
                      </>
                    ) : (
                      <>
                        Upload & Configure <ArrowRight className="h-4 w-4 ml-2" />
                      </>
                    )}
                  </Button>
                </div>
              )}
            </div>

            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start">
                <AlertCircle className="h-5 w-5 text-red-600 mr-2 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-red-800 font-medium">Upload Failed</p>
                  <p className="text-red-600 text-sm">{error}</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {dataType === ('pii_masking' as DataType) && (
        <Card>
          <CardHeader>
            <CardTitle>Upload Dataset for PII Masking</CardTitle>
            <CardDescription>
              Upload a CSV or Excel file to auto-detect and anonymize personally identifiable information
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div
              className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors
                border-gray-300 hover:border-rose-400 ${piiUploading ? 'opacity-50 cursor-not-allowed' : ''}`}
              onClick={() => !piiUploading && document.getElementById('pii-file-input')?.click()}
            >
              <input
                type="file"
                accept=".csv,.xlsx,.xls"
                className="hidden"
                id="pii-file-input"
                onChange={(e) => {
                  if (e.target.files) handlePIIUpload(Array.from(e.target.files));
                }}
              />
              {piiUploading ? (
                <div className="flex flex-col items-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-rose-600 mb-4" />
                  <p className="text-gray-600">Uploading and detecting PII...</p>
                </div>
              ) : (
                <div className="flex flex-col items-center">
                  <UploadIcon className="h-12 w-12 text-gray-400 mb-4" />
                  <p className="text-gray-700 font-medium mb-2">Upload CSV or Excel file</p>
                  <p className="text-gray-500 text-sm">We'll auto-detect PII columns like emails, SSNs, phones, etc.</p>
                </div>
              )}
            </div>
            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start">
                <AlertCircle className="h-5 w-5 text-red-600 mr-2 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-red-800 font-medium">Upload Failed</p>
                  <p className="text-red-600 text-sm">{error}</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {dataType === ('log_synthesis' as DataType) && (
        <Card>
          <CardHeader>
            <CardTitle>Upload Log File</CardTitle>
            <CardDescription>
              Upload a sample log file to generate synthetic logs preserving format and patterns
            </CardDescription>
          </CardHeader>
          <CardContent>
            <LogUploader
              onUploadSuccess={handleLogUploadSuccess}
              onUploadError={handleUploadError}
            />
            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start">
                <AlertCircle className="h-5 w-5 text-red-600 mr-2 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-red-800 font-medium">Upload Failed</p>
                  <p className="text-red-600 text-sm">{error}</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {dataType === ('cdc_testing' as DataType) && (
        <Card>
          <CardHeader>
            <CardTitle>Upload Database Schema for CDC</CardTitle>
            <CardDescription>
              Upload a database schema (SQL DDL, JSON, or YAML) to generate CDC event streams
            </CardDescription>
          </CardHeader>
          <CardContent>
            <DBSchemaUploader
              onUploadSuccess={(_jobId: string) => {
                // Re-upload via CDC endpoint
              }}
              onUploadError={handleUploadError}
            />
            <div className="mt-4">
              <p className="text-sm text-gray-500 mb-3">Or upload directly for CDC generation:</p>
              <input
                type="file"
                accept=".sql,.ddl,.json,.yaml,.yml"
                className="hidden"
                id="cdc-file-input"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) handleCDCUpload(e.target.files[0]);
                }}
              />
              <Button
                onClick={() => document.getElementById('cdc-file-input')?.click()}
                disabled={cdcUploading}
                variant="outline"
                className="w-full"
              >
                {cdcUploading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-cyan-600 mr-2" />
                    Uploading...
                  </>
                ) : (
                  <>Select Schema File for CDC</>
                )}
              </Button>
            </div>
            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start">
                <AlertCircle className="h-5 w-5 text-red-600 mr-2 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-red-800 font-medium">Upload Failed</p>
                  <p className="text-red-600 text-sm">{error}</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {dataType === ('graph_synthesis' as DataType) && (
        <Card>
          <CardHeader>
            <CardTitle>Upload Graph Data</CardTitle>
            <CardDescription>
              Upload a graph file (CSV edge list, JSON, or GraphML) to synthesize matching networks
            </CardDescription>
          </CardHeader>
          <CardContent>
            <GraphUploader
              onUploadSuccess={handleGraphUploadSuccess}
              onUploadError={handleUploadError}
            />
            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start">
                <AlertCircle className="h-5 w-5 text-red-600 mr-2 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-red-800 font-medium">Upload Failed</p>
                  <p className="text-red-600 text-sm">{error}</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Quick Links */}
      <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
        <button
          onClick={() => navigate('/history')}
          className="flex flex-col items-center p-4 bg-white border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors"
        >
          <History className="h-6 w-6 text-gray-500 mb-2" />
          <span className="text-sm font-medium text-gray-700">Job History</span>
        </button>
        <button
          onClick={() => navigate('/compare')}
          className="flex flex-col items-center p-4 bg-white border border-gray-200 rounded-lg hover:border-green-300 hover:bg-green-50 transition-colors"
        >
          <ArrowLeftRight className="h-6 w-6 text-gray-500 mb-2" />
          <span className="text-sm font-medium text-gray-700">Compare</span>
        </button>
        <button
          onClick={() => navigate('/drift')}
          className="flex flex-col items-center p-4 bg-white border border-gray-200 rounded-lg hover:border-purple-300 hover:bg-purple-50 transition-colors"
        >
          <Activity className="h-6 w-6 text-gray-500 mb-2" />
          <span className="text-sm font-medium text-gray-700">Drift Detection</span>
        </button>
        <button
          onClick={() => navigate('/settings')}
          className="flex flex-col items-center p-4 bg-white border border-gray-200 rounded-lg hover:border-amber-300 hover:bg-amber-50 transition-colors"
        >
          <Settings className="h-6 w-6 text-gray-500 mb-2" />
          <span className="text-sm font-medium text-gray-700">Settings</span>
        </button>
      </div>
    </div>
  );
}
