import { useState } from 'react';
import ErrorDisplay from '../components/ErrorDisplay';
import IncidentReportView from '../components/IncidentReport';
import InvestigationForm from '../components/InvestigationForm';
import type { IncidentReport, InvestigationInput } from '../types';
import { ApiError, investigate } from '../api/client';

function Home() {
  const [isLoading, setIsLoading] = useState(false);
  const [report, setReport] = useState<IncidentReport | null>(null);
  const [error, setError] = useState<{ code: string; message: string; details?: string } | null>(
    null
  );

  const handleSubmit = async (input: InvestigationInput) => {
    setIsLoading(true);
    setError(null);
    setReport(null);

    try {
      const result = await investigate(input);
      setReport(result);
    } catch (err) {
      if (err instanceof ApiError) {
        setError({
          code: err.code,
          message: err.message,
          details: err.details,
        });
      } else if (err instanceof Error) {
        setError({
          code: 'NETWORK_ERROR',
          message: err.message || 'An unexpected error occurred.',
        });
      } else {
        setError({
          code: 'UNKNOWN_ERROR',
          message: 'An unexpected error occurred.',
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="home-page">
      <section className="form-section">
        <InvestigationForm onSubmit={handleSubmit} isLoading={isLoading} />
      </section>

      {error && (
        <section className="error-section">
          <ErrorDisplay
            code={error.code}
            message={error.message}
            details={error.details}
            onDismiss={() => setError(null)}
          />
        </section>
      )}

      {report && (
        <section className="report-section-container">
          <IncidentReportView report={report} />
        </section>
      )}
    </div>
  );
}

export default Home;
