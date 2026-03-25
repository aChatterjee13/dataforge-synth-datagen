import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Button } from '../components/Button';
import PDFResults from '../components/PDFResults';

export default function PDFResultsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  if (!jobId) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <p className="text-red-600">Invalid job ID</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-8">
        <Button
          variant="outline"
          onClick={() => navigate('/upload')}
          className="mb-4"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          New Generation
        </Button>
        <h1 className="text-3xl font-bold mb-2">Synthetic PDF Results</h1>
        <p className="text-gray-600">Your generated PDFs are ready for download</p>
      </div>

      <PDFResults jobId={jobId} />
    </div>
  );
}
