import { useState } from 'react';
import type { IncidentReport as IncidentReportType, IssueData } from '../types';
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

interface CollapsibleSectionProps {
  icon: string;
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

function CollapsibleSection({ title, defaultOpen = true, children }: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="report-section">
      <div
        className="report-section__header"
        onClick={() => setIsOpen(!isOpen)}
        role="button"
        tabIndex={0}
        aria-expanded={isOpen}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setIsOpen(!isOpen); }}
      >
        <h2>{title}</h2>
        <span className={`report-section__toggle ${!isOpen ? 'report-section__toggle--collapsed' : ''}`}>
          ▼
        </span>
      </div>
      {isOpen && children}
    </div>
  );
}

function IssueCard({ issue }: { issue: IssueData }) {
  return (
    <div className="issue-card">
      <div className="issue-card__header">
        <span className="issue-number">#{issue.number}</span>
        <a
          href={issue.url}
          target="_blank"
          rel="noopener noreferrer"
          className="issue-title-link"
        >
          {issue.title}
        </a>
        <span className={`issue-state issue-state--${issue.state}`}>
          {issue.state}
        </span>
      </div>
      {issue.labels.length > 0 && (
        <div className="issue-labels">
          {issue.labels.map((label) => (
            <span key={label} className="issue-label">{label}</span>
          ))}
        </div>
      )}
      {issue.body && (
        <p className="issue-body">
          {issue.body.length > 200 ? issue.body.substring(0, 200) + '...' : issue.body}
        </p>
      )}
    </div>
  );
}

function IncidentReport({ report }: IncidentReportProps) {
  return (
    <div className="incident-report">
      <CollapsibleSection icon="📅" title="Investigation Window">
        <p>
          <strong>Start:</strong> {new Date(report.timeWindow.start).toLocaleString()}
          <br />
          <strong>End:</strong> {new Date(report.timeWindow.end).toLocaleString()}
        </p>
      </CollapsibleSection>

      <CollapsibleSection icon="🕐" title="Timeline">
        <Timeline entries={report.timeline} />
      </CollapsibleSection>

      {report.issues && report.issues.length > 0 && (
        <CollapsibleSection icon="📋" title="Issues">
          <div className="issues-list">
            {report.issues.map((issue) => (
              <IssueCard key={issue.number} issue={issue} />
            ))}
          </div>
        </CollapsibleSection>
      )}

      <CollapsibleSection icon="🔍" title="Suspicious Commits">
        {report.suspiciousCommits.length === 0 ? (
          <p className="empty-state">
            No commits were identified as suspicious within the time window.
          </p>
        ) : (
          <div className="suspicious-commits">
            {report.suspiciousCommits.map((commit) => (
              <div
                key={commit.sha}
                className={`commit-card commit-card--${commit.confidence.toLowerCase()}`}
              >
                <div className="commit-card__header">
                  <code className="commit-sha">{commit.sha.substring(0, 8)}</code>
                  <ConfidenceBadge confidence={commit.confidence} />
                </div>
                <p className="commit-card__explanation">{commit.explanation}</p>
              </div>
            ))}
          </div>
        )}
      </CollapsibleSection>

      <CollapsibleSection icon="🎯" title="Root Cause">
        <div className="root-cause">
          <p>{report.rootCause}</p>
        </div>
      </CollapsibleSection>

      <CollapsibleSection icon="⏪" title="Suggested Rollback">
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
      </CollapsibleSection>
    </div>
  );
}

export default IncidentReport;
