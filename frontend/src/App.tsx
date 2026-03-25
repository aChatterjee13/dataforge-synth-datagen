import { Component, type ErrorInfo, type ReactNode } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Upload from './pages/Upload';
import Configure from './pages/Configure';
import ConfigurePDF from './pages/ConfigurePDF';
import ConfigureAPITest from './pages/ConfigureAPITest';
import ConfigureDBTest from './pages/ConfigureDBTest';
import Generate from './pages/Generate';
import Results from './pages/Results';
import PDFResults from './pages/PDFResults';
import APITestResults from './pages/APITestResults';
import DBTestResults from './pages/DBTestResults';
import JobHistory from './pages/JobHistory';
import Compare from './pages/Compare';
import DriftDetection from './pages/DriftDetection';
import Settings from './pages/Settings';
import ConfigureMultiTable from './pages/ConfigureMultiTable';
import ConfigurePII from './pages/ConfigurePII';
import ConfigureLogs from './pages/ConfigureLogs';
import ConfigureCDC from './pages/ConfigureCDC';
import ConfigureGraph from './pages/ConfigureGraph';
import PIIResults from './pages/PIIResults';
import LogResults from './pages/LogResults';
import CDCResults from './pages/CDCResults';
import GraphResults from './pages/GraphResults';

// Error Boundary Component
class ErrorBoundary extends Component<
  { children: ReactNode; componentName: string },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: ReactNode; componentName: string }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(`Error in ${this.props.componentName}:`, error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '50px', backgroundColor: '#fee', color: '#c00' }}>
          <h1>Error in {this.props.componentName}</h1>
          <pre>{this.state.error?.message}</pre>
          <pre>{this.state.error?.stack}</pre>
        </div>
      );
    }

    return this.props.children;
  }
}

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Routes>
          <Route path="/" element={
            <ErrorBoundary componentName="Upload">
              <Upload />
            </ErrorBoundary>
          } />
          <Route path="/configure/:jobId" element={
            <ErrorBoundary componentName="Configure">
              <Configure />
            </ErrorBoundary>
          } />
          <Route path="/configure-pdf/:jobId" element={
            <ErrorBoundary componentName="ConfigurePDF">
              <ConfigurePDF />
            </ErrorBoundary>
          } />
          <Route path="/configure-api-test/:jobId" element={
            <ErrorBoundary componentName="ConfigureAPITest">
              <ConfigureAPITest />
            </ErrorBoundary>
          } />
          <Route path="/configure-db-test/:jobId" element={
            <ErrorBoundary componentName="ConfigureDBTest">
              <ConfigureDBTest />
            </ErrorBoundary>
          } />
          <Route path="/generate/:jobId" element={
            <ErrorBoundary componentName="Generate">
              <Generate />
            </ErrorBoundary>
          } />
          <Route path="/results/:jobId" element={
            <ErrorBoundary componentName="Results">
              <Results />
            </ErrorBoundary>
          } />
          <Route path="/pdf-results/:jobId" element={
            <ErrorBoundary componentName="PDFResults">
              <PDFResults />
            </ErrorBoundary>
          } />
          <Route path="/api-test-results/:jobId" element={
            <ErrorBoundary componentName="APITestResults">
              <APITestResults />
            </ErrorBoundary>
          } />
          <Route path="/db-test-results/:jobId" element={
            <ErrorBoundary componentName="DBTestResults">
              <DBTestResults />
            </ErrorBoundary>
          } />
          <Route path="/history" element={
            <ErrorBoundary componentName="JobHistory">
              <JobHistory />
            </ErrorBoundary>
          } />
          <Route path="/compare" element={
            <ErrorBoundary componentName="Compare">
              <Compare />
            </ErrorBoundary>
          } />
          <Route path="/drift" element={
            <ErrorBoundary componentName="DriftDetection">
              <DriftDetection />
            </ErrorBoundary>
          } />
          <Route path="/settings" element={
            <ErrorBoundary componentName="Settings">
              <Settings />
            </ErrorBoundary>
          } />
          <Route path="/configure-multi/:jobId" element={
            <ErrorBoundary componentName="ConfigureMultiTable">
              <ConfigureMultiTable />
            </ErrorBoundary>
          } />
          <Route path="/configure-pii/:jobId" element={
            <ErrorBoundary componentName="ConfigurePII">
              <ConfigurePII />
            </ErrorBoundary>
          } />
          <Route path="/configure-logs/:jobId" element={
            <ErrorBoundary componentName="ConfigureLogs">
              <ConfigureLogs />
            </ErrorBoundary>
          } />
          <Route path="/configure-cdc/:jobId" element={
            <ErrorBoundary componentName="ConfigureCDC">
              <ConfigureCDC />
            </ErrorBoundary>
          } />
          <Route path="/configure-graph/:jobId" element={
            <ErrorBoundary componentName="ConfigureGraph">
              <ConfigureGraph />
            </ErrorBoundary>
          } />
          <Route path="/pii-results/:jobId" element={
            <ErrorBoundary componentName="PIIResults">
              <PIIResults />
            </ErrorBoundary>
          } />
          <Route path="/log-results/:jobId" element={
            <ErrorBoundary componentName="LogResults">
              <LogResults />
            </ErrorBoundary>
          } />
          <Route path="/cdc-results/:jobId" element={
            <ErrorBoundary componentName="CDCResults">
              <CDCResults />
            </ErrorBoundary>
          } />
          <Route path="/graph-results/:jobId" element={
            <ErrorBoundary componentName="GraphResults">
              <GraphResults />
            </ErrorBoundary>
          } />
          <Route path="*" element={
            <div className="flex flex-col items-center justify-center min-h-screen">
              <h1 className="text-2xl font-bold text-gray-800 mb-4">Page not found</h1>
              <Link to="/" className="text-blue-600 hover:underline">Go home</Link>
            </div>
          } />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
