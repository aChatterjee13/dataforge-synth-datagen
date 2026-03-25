import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Button } from '../components/Button';
import PIIResultsDashboard from '../components/PIIResultsDashboard';

export default function PIIResultsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  if (!jobId) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <p className="text-red-600">Invalid job ID</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="mb-8">
        <Button
          variant="outline"
          onClick={() => navigate('/')}
          className="mb-4"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Home
        </Button>
        <h1 className="text-3xl font-bold mb-2">PII Masking Results</h1>
        <p className="text-gray-600">Review your masked dataset and privacy assessment</p>
      </div>

      <PIIResultsDashboard jobId={jobId} />
    </div>
  );
}
