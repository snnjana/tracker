import { useState } from 'react';
import type { IncidentReport as IncidentReportType } from '../types';
import Timeline from './Timeline';

interface IncidentReportProps {
  report: IncidentReportType;
}

function ConfidenceBadge({ confidence }: { confidence: 'High' | 'Medium' | 'Low' }) {
  const classMap = {
    High: 'badge badge--high',
    Medium: 'badge badge--medium',
    Low: 'badge badge--low',
  };

  return <span className={classMap[confidence]}>{confidence}</span>;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      const textarea = document.createElement('textarea');
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <button className="copy-btn" onClick={handleCopy} aria-label="Copy to clipboard">
      {copied ? '✓ Copied' : '📋 Copy'}
    </button>
  );
}

function IncidentReport({ report }: IncidentReportProps) {
  return (
    <div className="incident-report">
      <div className="report-section">
        <h2>📅 Investigation Window</h2>
        <p>
          <strong>Start:</strong> {new Date(report.timeWindow.start).toLocaleString()}
          <br />
          <strong>End:</strong> {new Date(report.timeWindow.end).toLocaleString()}
        </p>
      </div>

      <div className="report-section">
        <h2>🕐 Timeline</h2>
        <Timeline entries={report.timeline} />
      </div>

      <div className="report-section">
        <h2>🔍 Suspicious Commits</h2>
        {report.suspiciousCommits.length === 0 ? (
          <p className="empty-state">
            No commits were identified as suspicious within the time window.
          </p>
        ) : (
          <div className="suspicious-commits">
            {report.suspiciousCommits.map((commit) => (
              <div key={commit.sha} className="commit-card">
                <div className="commit-card__header">
                  <code className="commit-sha">{commit.sha.substring(0, 8)}</code>
                  <ConfidenceBadge confidence={commit.confidence} />
                </div>
                <p className="commit-card__explanation">{commit.explanation}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="report-section">
        <h2>🎯 Root Cause</h2>
        <div className="root-cause">
          <p>{report.rootCause}</p>
        </div>
      </div>

      <div className="report-section">
        <h2>⏪ Suggested Rollback</h2>
        {report.suggestedRollback.length === 0 ? (
          <p className="empty-state">No rollback suggestions.</p>
        ) : (
          <div className="rollback-suggestions">
            {report.suggestedRollback.map((rb) => (
              <div key={rb.sha} className="rollback-item">
                <div className="rollback-item__header">
                  <code className="commit-sha">{rb.sha.substring(0, 8)}</code>
                </div>
                <div className="code-block">
                  <pre><code>{rb.command}</code></pre>
                  <CopyButton text={rb.command} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default IncidentReport;
