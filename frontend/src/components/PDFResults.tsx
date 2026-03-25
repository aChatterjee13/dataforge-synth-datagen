import { useState, useEffect } from 'react';
import { FileText, Download, Package } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './Card';
import { Button } from './Button';
import { listPDFs, downloadPDF as getDownloadPDFUrl, downloadPDFsZip as getDownloadPDFsZipUrl } from '../services/api';
import { getApiErrorMessage } from '../lib/utils';
import type { PDFListResponse } from '../types';

interface PDFResultsProps {
  jobId: string;
}

export default function PDFResults({ jobId }: PDFResultsProps) {
  const [pdfList, setPdfList] = useState<PDFListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPDFList();
  }, [jobId]);

  const fetchPDFList = async () => {
    try {
      const data = await listPDFs(jobId);
      setPdfList(data);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPDF = (filename: string) => {
    window.open(getDownloadPDFUrl(jobId, filename), '_blank');
  };

  const downloadAllZip = () => {
    window.open(getDownloadPDFsZipUrl(jobId), '_blank');
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="text-center text-gray-600">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4" />
            <p>Loading generated PDFs...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-red-200 bg-red-50">
        <CardContent className="py-8">
          <div className="text-center text-red-600">
            <p className="font-medium">Error loading PDFs</p>
            <p className="text-sm mt-1">{error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!pdfList || pdfList.total_pdfs === 0) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="text-center text-gray-600">
            <p>No PDFs generated yet</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center">
            <FileText className="h-5 w-5 mr-2 text-purple-600" />
            Generated PDFs ({pdfList.total_pdfs})
          </CardTitle>
          <Button
            onClick={downloadAllZip}
            className="bg-purple-600 hover:bg-purple-700"
          >
            <Package className="h-4 w-4 mr-2" />
            Download All (ZIP)
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {pdfList.pdfs.map((pdf, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-purple-300 transition-colors"
            >
              <div className="flex items-center">
                <FileText className="h-8 w-8 text-purple-600 mr-3" />
                <div>
                  <p className="font-medium text-gray-900">{pdf.filename}</p>
                  <p className="text-sm text-gray-500">{formatFileSize(pdf.size)}</p>
                </div>
              </div>
              <Button
                variant="outline"
                onClick={() => handleDownloadPDF(pdf.filename)}
                className="ml-4"
              >
                <Download className="h-4 w-4 mr-2" />
                Download
              </Button>
            </div>
          ))}
        </div>

        <div className="mt-6 p-4 bg-purple-50 border border-purple-200 rounded-lg">
          <p className="text-sm text-purple-900">
            <strong>Generated:</strong> {pdfList.total_pdfs} synthetic PDF{pdfList.total_pdfs > 1 ? 's' : ''}
          </p>
          <p className="text-xs text-purple-700 mt-1">
            Each PDF contains unique content while preserving the style and structure of the original samples
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
