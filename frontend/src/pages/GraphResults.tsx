import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '../components/Button';
import GraphResultsDashboard from '../components/GraphResultsDashboard';

export default function GraphResults() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="mb-8">
        <Button variant="outline" onClick={() => navigate('/')} className="mb-4">
          &larr; Back to Home
        </Button>
        <h1 className="text-3xl font-bold mb-2">Graph Synthesis Results</h1>
        <p className="text-gray-600">
          Synthetic graph generation and structural comparison
        </p>
      </div>

      {jobId && <GraphResultsDashboard jobId={jobId} />}
    </div>
  );
}
