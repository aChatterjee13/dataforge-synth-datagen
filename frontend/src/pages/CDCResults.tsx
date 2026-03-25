import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '../components/Button';
import CDCResultsDashboard from '../components/CDCResultsDashboard';

export default function CDCResults() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="mb-8">
        <Button variant="outline" onClick={() => navigate('/')} className="mb-4">
          ← Back to Home
        </Button>
        <h1 className="text-3xl font-bold mb-2">CDC Event Results</h1>
        <p className="text-gray-600">Generated Change Data Capture event stream</p>
      </div>

      {jobId && <CDCResultsDashboard jobId={jobId} />}
    </div>
  );
}
