import { useState, useMemo } from 'react';
import type { InvestigationInput } from '../types';
import { Eye, EyeOff } from 'lucide-react';

interface InvestigationFormProps {
  onSubmit: (input: InvestigationInput) => void;
  isLoading: boolean;
}

const MAX_RANGE_DAYS = 7;

function toLocalDatetimeString(date: Date): string {
  const offset = date.getTimezoneOffset();
  const local = new Date(date.getTime() - offset * 60 * 1000);
  return local.toISOString().slice(0, 16);
}

function InvestigationForm({ onSubmit, isLoading }: InvestigationFormProps) {
  const [repoUrl, setRepoUrl] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [showToken, setShowToken] = useState(false);

  // Calculate min/max constraints for end time based on start time
  const endTimeConstraints = useMemo(() => {
    if (!startTime) return { min: undefined, max: undefined };

    const startDate = new Date(startTime);
    const minEnd = startDate; // end must be after start
    const maxEnd = new Date(startDate.getTime() + MAX_RANGE_DAYS * 24 * 60 * 60 * 1000);

    return {
      min: toLocalDatetimeString(minEnd),
      max: toLocalDatetimeString(maxEnd),
    };
  }, [startTime]);

  // Calculate min/max constraints for start time based on end time
  const startTimeConstraints = useMemo(() => {
    if (!endTime) return { min: undefined, max: undefined };

    const endDate = new Date(endTime);
    const minStart = new Date(endDate.getTime() - MAX_RANGE_DAYS * 24 * 60 * 60 * 1000);
    const maxStart = endDate; // start must be before end

    return {
      min: toLocalDatetimeString(minStart),
      max: toLocalDatetimeString(maxStart),
    };
  }, [endTime]);

  // Show duration between selected dates
  const durationLabel = useMemo(() => {
    if (!startTime || !endTime) return null;
    const start = new Date(startTime);
    const end = new Date(endTime);
    const diffMs = end.getTime() - start.getTime();
    if (diffMs <= 0) return 'Invalid range';
    const hours = Math.round(diffMs / (1000 * 60 * 60));
    if (hours < 24) return `Duration: ${hours}h`;
    const days = (hours / 24).toFixed(1);
    return `Duration: ${days} days`;
  }, [startTime, endTime]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const input: InvestigationInput = {
      repoUrl,
      timeRange: {
        start: new Date(startTime).toISOString(),
        end: new Date(endTime).toISOString(),
      },
    };

    if (githubToken.trim()) {
      input.githubToken = githubToken.trim();
    }

    onSubmit(input);
  };

  return (
    <form className="investigation-form" onSubmit={handleSubmit}>
      <div className="form-group">
        <label htmlFor="repo-url">GitHub Repository URL</label>
        <input
          id="repo-url"
          type="url"
          placeholder="https://github.com/owner/repo"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          required
        />
      </div>

      <div className="form-group">
        <label htmlFor="github-token">
          GitHub Token <span className="hint">(required for private repos, recommended to avoid rate limits)</span>
        </label>
        <div className="token-input-wrapper">
          <input
            id="github-token"
            type="text"
            style={{ WebkitTextSecurity: showToken ? 'none' : 'disc' }}
            placeholder="ghp_xxxxxxxxxxxx"
            value={githubToken}
            onChange={(e) => setGithubToken(e.target.value)}
            autoComplete="off"
          />
          <button
            type="button"
            className="token-toggle-btn"
            onClick={() => setShowToken(!showToken)}
            aria-label={showToken ? 'Hide token' : 'Show token'}
          >
            {showToken ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
        <span className="hint token-hint">
          Saved in your browser only. Generate at{' '}
          <a href="https://github.com/settings/tokens" target="_blank" rel="noopener noreferrer">
            github.com/settings/tokens
          </a>
        </span>
      </div>

      <div className="form-group">
        <label>Investigation Window <span className="hint">(max 7 days between start and end)</span></label>
        <div className="time-range-inputs">
          <div>
            <label htmlFor="start-time">Start</label>
            <input
              id="start-time"
              type="datetime-local"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              min={startTimeConstraints.min}
              max={startTimeConstraints.max}
              required
            />
          </div>
          <div>
            <label htmlFor="end-time">End</label>
            <input
              id="end-time"
              type="datetime-local"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
              min={endTimeConstraints.min}
              max={endTimeConstraints.max}
              required
            />
          </div>
        </div>
        {durationLabel && (
          <span className="time-label">{durationLabel}</span>
        )}
      </div>

      <button type="submit" className="submit-btn" disabled={isLoading}>
        {isLoading ? (
          <span className="loading-indicator">
            <span className="spinner" aria-hidden="true"></span>
            Investigating...
          </span>
        ) : (
          'Start Investigation'
        )}
      </button>
    </form>
  );
}

export default InvestigationForm;
