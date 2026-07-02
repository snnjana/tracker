import type { TimelineEntry } from '../types';

interface TimelineProps {
  entries: TimelineEntry[];
}

function getTypeIcon(type: TimelineEntry['type']): string {
  switch (type) {
    case 'commit':
      return '🔀';
    case 'log_event':
      return '📋';
    case 'metric_data_point':
      return '📈';
    default:
      return '•';
  }
}

function getTypeLabel(type: TimelineEntry['type']): string {
  switch (type) {
    case 'commit':
      return 'Commit';
    case 'log_event':
      return 'Log Event';
    case 'metric_data_point':
      return 'Metric';
    default:
      return 'Event';
  }
}

function formatTimestamp(timestamp: string): string {
  try {
    return new Date(timestamp).toLocaleString();
  } catch {
    return timestamp;
  }
}

function Timeline({ entries }: TimelineProps) {
  if (entries.length === 0) {
    return <p className="empty-state">No timeline entries found.</p>;
  }

  return (
    <div className="timeline">
      {entries.map((entry, index) => (
        <div key={index} className={`timeline-entry timeline-entry--${entry.type}`}>
          <div className="timeline-entry__icon" aria-label={getTypeLabel(entry.type)}>
            {getTypeIcon(entry.type)}
          </div>
          <div className="timeline-entry__content">
            <div className="timeline-entry__header">
              <span className="timeline-entry__type">{getTypeLabel(entry.type)}</span>
              <time className="timeline-entry__time">
                {formatTimestamp(entry.timestamp)}
              </time>
            </div>
            <p className="timeline-entry__summary">{entry.summary}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

export default Timeline;
