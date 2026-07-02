interface ErrorDisplayProps {
  code: string;
  message: string;
  details?: string;
  onDismiss?: () => void;
}

function ErrorDisplay({ code, message, details, onDismiss }: ErrorDisplayProps) {
  return (
    <div className="error-display" role="alert">
      <div className="error-display__header">
        <span className="error-display__icon" aria-hidden="true">⚠️</span>
        <span className="error-display__code">{code}</span>
        {onDismiss && (
          <button
            className="error-display__dismiss"
            onClick={onDismiss}
            aria-label="Dismiss error"
          >
            ✕
          </button>
        )}
      </div>
      <p className="error-display__message">{message}</p>
      {details && (
        <details className="error-display__details">
          <summary>Details</summary>
          <pre>{details}</pre>
        </details>
      )}
    </div>
  );
}

export default ErrorDisplay;
