/** TypeScript interfaces matching the backend Pydantic models. */

export interface TimeRange {
  start: string;
  end: string;
}

export interface MetricQuery {
  metricName: string;
  namespace: string;
  dimensions?: Record<string, string>;
}

export interface InvestigationInput {
  repoUrl: string;
  timeRange: TimeRange;
}

export interface TimeWindow {
  start: string;
  end: string;
}

export interface CommitData {
  sha: string;
  author: string;
  authorEmail: string;
  timestamp: string;
  message: string;
  changedFiles: string[];
}

export interface LogEvent {
  timestamp: string;
  logGroup: string;
  logStream: string;
  message: string;
}

export interface MetricDataPoint {
  timestamp: string;
  metricName: string;
  namespace: string;
  value: number;
  unit: string;
}

export interface SuspiciousCommit {
  sha: string;
  confidence: 'High' | 'Medium' | 'Low';
  explanation: string;
}

export interface RollbackSuggestion {
  sha: string;
  command: string;
}

export interface TimelineEntry {
  timestamp: string;
  type: 'commit' | 'log_event' | 'metric_data_point';
  summary: string;
  details: Record<string, unknown>;
}

export interface IssueData {
  number: number;
  title: string;
  state: string;
  createdAt: string;
  updatedAt: string;
  labels: string[];
  body?: string;
  url: string;
}

export interface IncidentReport {
  timeWindow: TimeWindow;
  timeline: TimelineEntry[];
  suspiciousCommits: SuspiciousCommit[];
  rootCause: string;
  suggestedRollback: RollbackSuggestion[];
  issues?: IssueData[];
}

export interface ErrorResponse {
  code: string;
  message: string;
  details?: string;
}
