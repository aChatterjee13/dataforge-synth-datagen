import axios from 'axios';
import type {
  UploadResponse,
  GenerationConfig,
  JobStatusResponse,
  ValidationResponse,
  JobListItem,
  PDFListResponse,
  PDFInfo,
  GenerateResponse,
  CDCSchemaUploadResponse,
  APITestResultsResponse,
  DBTestResultsResponse,
  Preset,
  ModelRecommendation,
  APIKeyItem,
  APIKeyCreateResponse,
  MultiTableUploadResponse,
  DriftResult,
  DriftColumnInfo,
  PreviewData,
  PIIUploadResponse,
  PIIResultsResponse,
  LogUploadResponse,
  LogResultsResponse,
  CDCResultsResponse,
  GraphUploadResponse,
  GraphResultsResponse,
} from '../types';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const uploadDataset = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

export const generateSynthetic = async (
  jobId: string,
  config: GenerationConfig
): Promise<void> => {
  await api.post('/generate', {
    job_id: jobId,
    config,
  });
};

export const getJobStatus = async (jobId: string): Promise<JobStatusResponse> => {
  const response = await api.get(`/status/${jobId}`);
  return response.data;
};

export const getValidation = async (jobId: string): Promise<ValidationResponse> => {
  const response = await api.get(`/validation/${jobId}`);
  return response.data;
};

export const downloadSynthetic = (jobId: string): string => {
  return `${API_BASE_URL}/download/${jobId}`;
};

export const downloadSyntheticBlob = async (jobId: string): Promise<Blob> => {
  const response = await api.get(`/download/${jobId}`, { responseType: 'blob' });
  return response.data;
};

export const listJobs = async (): Promise<JobListItem[]> => {
  const response = await api.get('/jobs');
  return response.data.jobs;
};

export const deleteJob = async (jobId: string): Promise<void> => {
  await api.delete(`/jobs/${jobId}`);
};

// PDF-related API functions

export const uploadPDFs = async (files: File[]): Promise<{ job_id: string; pdf_info: PDFInfo[] }> => {
  const formData = new FormData();
  files.forEach(file => {
    formData.append('files', file);
  });

  const response = await api.post('/upload-pdfs', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

export const generatePDFs = async (
  jobId: string,
  config: Record<string, unknown>
): Promise<GenerateResponse> => {
  const response = await api.post('/generate-pdfs', {
    job_id: jobId,
    config,
  });

  return response.data;
};

export const listPDFs = async (jobId: string): Promise<PDFListResponse> => {
  const response = await api.get(`/list-pdfs/${jobId}`);
  return response.data;
};

export const downloadPDF = (jobId: string, filename: string): string => {
  return `${API_BASE_URL}/download-pdf/${jobId}/${filename}`;
};

export const downloadPDFsZip = (jobId: string): string => {
  return `${API_BASE_URL}/download-pdfs-zip/${jobId}`;
};

// API Testing functions

export const uploadAPISpec = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/upload-api-spec', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

  return response.data;
};

export const generateAPITests = async (
  jobId: string,
  config: Record<string, unknown>
): Promise<GenerateResponse> => {
  const response = await api.post('/generate-api-tests', {
    job_id: jobId,
    config,
  });
  return response.data;
};

export const getAPITestResults = async (jobId: string): Promise<APITestResultsResponse> => {
  const response = await api.get(`/api-test-results/${jobId}`);
  return response.data;
};

export const downloadAPITests = (jobId: string, type: string = 'postman'): string => {
  return `${API_BASE_URL}/download-api-tests/${jobId}?type=${type}`;
};

// Data Testing functions

export const uploadDBSchema = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/upload-db-schema', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

  return response.data;
};

export const generateDBTests = async (
  jobId: string,
  config: Record<string, unknown>
): Promise<GenerateResponse> => {
  const response = await api.post('/generate-db-tests', {
    job_id: jobId,
    config,
  });
  return response.data;
};

export const getDBTestResults = async (jobId: string): Promise<DBTestResultsResponse> => {
  const response = await api.get(`/db-test-results/${jobId}`);
  return response.data;
};

export const downloadDBTests = (jobId: string, type: string = 'all'): string => {
  return `${API_BASE_URL}/download-db-tests/${jobId}?type=${type}`;
};


// ============================================================================
// COMPARE DATASETS (Feature 4)
// ============================================================================

export const compareDatasets = async (file1: File, file2: File): Promise<ValidationResponse> => {
  const formData = new FormData();
  formData.append('file1', file1);
  formData.append('file2', file2);

  const response = await api.post('/compare', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};


// ============================================================================
// PRESETS (Feature 5)
// ============================================================================

export const listPresets = async (): Promise<Preset[]> => {
  const response = await api.get('/presets');
  return response.data;
};

export const savePreset = async (name: string, description: string, config: Record<string, unknown>): Promise<Preset> => {
  const response = await api.post('/presets', { name, description, config });
  return response.data;
};

export const deletePreset = async (presetId: number): Promise<void> => {
  await api.delete(`/presets/${presetId}`);
};


// ============================================================================
// MODEL RECOMMENDATION (Feature 6)
// ============================================================================

export const getModelRecommendation = async (jobId: string, useCase: string = 'ml_training'): Promise<ModelRecommendation> => {
  const response = await api.get(`/recommend/${jobId}?use_case=${useCase}`);
  return response.data;
};


// ============================================================================
// API KEYS (Feature 8)
// ============================================================================

export const createAPIKey = async (name: string): Promise<APIKeyCreateResponse> => {
  const response = await api.post('/api-keys', { name });
  return response.data;
};

export const listAPIKeys = async (): Promise<APIKeyItem[]> => {
  const response = await api.get('/api-keys');
  return response.data;
};

export const deleteAPIKey = async (keyId: number): Promise<void> => {
  await api.delete(`/api-keys/${keyId}`);
};


// ============================================================================
// MULTI-TABLE (Feature 9)
// ============================================================================

export const uploadMultiTable = async (files: File[]): Promise<MultiTableUploadResponse> => {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));

  const response = await api.post('/upload-multi', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const generateMultiTable = async (
  jobId: string,
  config: Record<string, unknown>
): Promise<void> => {
  await api.post('/generate-multi', { job_id: jobId, config });
};


// ============================================================================
// DRIFT DETECTION (Feature 11)
// ============================================================================

export const detectDrift = async (
  baseline: File,
  snapshot: File,
  targetColumn?: string
): Promise<DriftResult> => {
  const formData = new FormData();
  formData.append('baseline', baseline);
  formData.append('snapshot', snapshot);
  if (targetColumn) {
    formData.append('target_column', targetColumn);
  }

  const response = await api.post('/drift-detect', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const getDriftColumns = async (file: File): Promise<DriftColumnInfo[]> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/drift-columns', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data.columns;
};


// ============================================================================
// STREAMING / PREVIEW (Feature 12)
// ============================================================================

export const streamGenerate = (jobId: string): EventSource => {
  return new EventSource(`${API_BASE_URL}/stream-generate/${jobId}`);
};

export const getPreview = async (jobId: string, n: number = 20): Promise<PreviewData> => {
  const response = await api.get(`/preview/${jobId}?n=${n}`);
  return response.data;
};


// ============================================================================
// PII MASKING
// ============================================================================

export const uploadPIIDataset = async (file: File): Promise<PIIUploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/upload-pii', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const generatePIIMask = async (
  jobId: string,
  config: Record<string, unknown>
): Promise<GenerateResponse> => {
  const response = await api.post('/generate-pii-mask', { job_id: jobId, config });
  return response.data;
};

export const getPIIResults = async (jobId: string): Promise<PIIResultsResponse> => {
  const response = await api.get(`/pii-results/${jobId}`);
  return response.data;
};

export const downloadPIIMasked = (jobId: string): string => {
  return `${API_BASE_URL}/download-pii/${jobId}`;
};


// ============================================================================
// LOG SYNTHESIS
// ============================================================================

export const uploadLogs = async (file: File): Promise<LogUploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/upload-logs', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const generateLogs = async (
  jobId: string,
  config: Record<string, unknown>
): Promise<GenerateResponse> => {
  const response = await api.post('/generate-logs', { job_id: jobId, config });
  return response.data;
};

export const getLogResults = async (jobId: string): Promise<LogResultsResponse> => {
  const response = await api.get(`/log-results/${jobId}`);
  return response.data;
};

export const downloadLogs = (jobId: string): string => {
  return `${API_BASE_URL}/download-logs/${jobId}`;
};


// ============================================================================
// CDC TESTING
// ============================================================================

export const uploadCDCSchema = async (file: File): Promise<CDCSchemaUploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/upload-cdc-schema', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const generateCDC = async (
  jobId: string,
  config: Record<string, unknown>
): Promise<GenerateResponse> => {
  const response = await api.post('/generate-cdc', { job_id: jobId, config });
  return response.data;
};

export const getCDCResults = async (jobId: string): Promise<CDCResultsResponse> => {
  const response = await api.get(`/cdc-results/${jobId}`);
  return response.data;
};

export const downloadCDC = (jobId: string): string => {
  return `${API_BASE_URL}/download-cdc/${jobId}`;
};


// ============================================================================
// GRAPH SYNTHESIS
// ============================================================================

export const uploadGraph = async (file: File): Promise<GraphUploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/upload-graph', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const generateGraph = async (
  jobId: string,
  config: Record<string, unknown>
): Promise<GenerateResponse> => {
  const response = await api.post('/generate-graph', { job_id: jobId, config });
  return response.data;
};

export const getGraphResults = async (jobId: string): Promise<GraphResultsResponse> => {
  const response = await api.get(`/graph-results/${jobId}`);
  return response.data;
};

export const downloadGraph = (jobId: string): string => {
  return `${API_BASE_URL}/download-graph/${jobId}`;
};
