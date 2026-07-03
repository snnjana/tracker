"""Pydantic models for the AI Incident Timeline Correlator."""

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class TimeRange(BaseModel):
    start: str = Field(..., description="Start timestamp in ISO 8601 format")
    end: str = Field(..., description="End timestamp in ISO 8601 format")


class MetricQuery(BaseModel):
    metric_name: str = Field(..., alias="metricName")
    namespace: str
    dimensions: Optional[Dict[str, str]] = None

    class Config:
        populate_by_name = True


class InvestigationInput(BaseModel):
    repo_url: str = Field(..., alias="repoUrl", description="GitHub repository URL")
    time_range: Optional[TimeRange] = Field(None, alias="timeRange")
    log_group_names: Optional[List[str]] = Field(None, alias="logGroupNames")
    metric_queries: Optional[List[MetricQuery]] = Field(None, alias="metricQueries")

    class Config:
        populate_by_name = True


class TimeWindow(BaseModel):
    start: datetime
    end: datetime


class CommitData(BaseModel):
    sha: str = Field(..., description="Full 40-character commit SHA")
    author: str
    author_email: str = Field(..., alias="authorEmail")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    message: str = Field(..., description="Commit message up to 72,000 chars")
    changed_files: List[str] = Field(default_factory=list, alias="changedFiles")
    patch: Optional[str] = Field(None, description="Combined diff/patch content for the commit")

    class Config:
        populate_by_name = True


class LogEvent(BaseModel):
    timestamp: str
    log_group: str = Field(..., alias="logGroup")
    log_stream: str = Field(..., alias="logStream")
    message: str = Field(..., description="Message content truncated to 4,000 chars")

    class Config:
        populate_by_name = True


class MetricDataPoint(BaseModel):
    timestamp: str
    metric_name: str = Field(..., alias="metricName")
    namespace: str
    value: float
    unit: str

    class Config:
        populate_by_name = True


class SuspiciousCommit(BaseModel):
    sha: str
    confidence: Literal["High", "Medium", "Low"]
    explanation: str


class RollbackSuggestion(BaseModel):
    sha: str
    command: str = Field(..., description='e.g., "git revert {sha}"')


class TimelineEntry(BaseModel):
    timestamp: str
    type: Literal["commit", "log_event", "metric_data_point"]
    summary: str
    details: Dict

    class Config:
        populate_by_name = True


class IssueData(BaseModel):
    number: int
    title: str
    state: str = Field(..., description="open or closed")
    created_at: str = Field(..., alias="createdAt")
    updated_at: str = Field(..., alias="updatedAt")
    labels: List[str] = Field(default_factory=list)
    body: Optional[str] = Field(None, description="Issue body truncated to 500 chars")
    url: str

    class Config:
        populate_by_name = True


class IncidentReport(BaseModel):
    time_window: TimeWindow = Field(..., alias="timeWindow")
    timeline: List[TimelineEntry]
    suspicious_commits: List[SuspiciousCommit] = Field(..., alias="suspiciousCommits")
    root_cause: str = Field(..., alias="rootCause", max_length=500)
    suggested_rollback: List[RollbackSuggestion] = Field(..., alias="suggestedRollback")
    issues: Optional[List[IssueData]] = Field(None, description="GitHub issues within the time window")

    class Config:
        populate_by_name = True


class AnalysisRequest(BaseModel):
    commits: List[CommitData]
    log_events: List[LogEvent] = Field(default_factory=list, alias="logEvents")
    metric_data_points: List[MetricDataPoint] = Field(
        default_factory=list, alias="metricDataPoints"
    )
    time_window: TimeWindow = Field(..., alias="timeWindow")

    class Config:
        populate_by_name = True


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[str] = None
