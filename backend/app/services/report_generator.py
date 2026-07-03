"""Transforms Bedrock analysis response into a structured IncidentReport."""

from typing import Any, Dict, List, Optional

from app.models import (
    IncidentReport,
    IssueData,
    RollbackSuggestion,
    SuspiciousCommit,
    TimelineEntry,
    TimeWindow,
)

MAX_ROOT_CAUSE_LENGTH = 500

# Priority for tie-breaking timeline entries with identical timestamps
TYPE_PRIORITY = {
    "commit": 0,
    "log_event": 1,
    "metric_data_point": 2,
}


def generate_report(
    analysis_result: Dict[str, Any], time_window: TimeWindow, issues: Optional[List[IssueData]] = None
) -> IncidentReport:
    """Transform Bedrock analysis output into a structured IncidentReport.

    Args:
        analysis_result: The parsed JSON response from Bedrock Claude.
        time_window: The investigation time window.

    Returns:
        A structured IncidentReport.
    """
    # Parse timeline entries
    timeline_raw = analysis_result.get("timeline", [])
    timeline: List[TimelineEntry] = []
    valid_types = {"commit", "log_event", "metric_data_point"}
    for entry in timeline_raw:
        entry_type = entry.get("type", "")
        # Skip entries with invalid types (LLM sometimes invents types)
        if entry_type not in valid_types:
            # Try to infer the type from the entry content
            summary = entry.get("summary", "").lower()
            if "commit" in summary or "sha" in str(entry.get("details", {})).lower():
                entry_type = "commit"
            elif "log" in summary or "error" in summary or "exception" in summary:
                entry_type = "log_event"
            elif "metric" in summary or "cpu" in summary or "memory" in summary:
                entry_type = "metric_data_point"
            else:
                entry_type = "log_event"  # Default fallback

        timeline.append(
            TimelineEntry(
                timestamp=entry.get("timestamp", ""),
                type=entry_type,
                summary=entry.get("summary", ""),
                details=entry.get("details", {}),
            )
        )

    # Sort timeline chronologically with tie-breaking
    timeline.sort(
        key=lambda e: (e.timestamp, TYPE_PRIORITY.get(e.type, 99))
    )

    # Parse suspicious commits (handle various key names)
    suspicious_raw = (
        analysis_result.get("suspiciousCommits")
        or analysis_result.get("suspicious_commits")
        or analysis_result.get("suspicious")
        or []
    )
    suspicious_commits: List[SuspiciousCommit] = []
    for commit in suspicious_raw:
        confidence = commit.get("confidence", commit.get("severity", "Low"))
        if confidence not in ("High", "Medium", "Low"):
            confidence = "Low"
        sha = commit.get("sha", commit.get("commit_sha", ""))
        explanation = commit.get("explanation", commit.get("reason", commit.get("description", "")))
        if sha:
            suspicious_commits.append(
                SuspiciousCommit(
                    sha=sha,
                    confidence=confidence,
                    explanation=explanation,
                )
            )

    # Parse root cause (truncate to 500 chars)
    root_cause = (
        analysis_result.get("rootCause")
        or analysis_result.get("root_cause")
        or analysis_result.get("rootcause")
        or "No root cause identified."
    )
    if len(root_cause) > MAX_ROOT_CAUSE_LENGTH:
        root_cause = root_cause[:MAX_ROOT_CAUSE_LENGTH]

    # Parse rollback suggestions (handle various key names the LLM might use)
    rollbacks_raw = (
        analysis_result.get("suggestedRollbacks")
        or analysis_result.get("suggested_rollbacks")
        or analysis_result.get("suggestedRollback")
        or analysis_result.get("rollbacks")
        or analysis_result.get("rollback_suggestions")
        or []
    )
    suggested_rollback: List[RollbackSuggestion] = []
    for rb in rollbacks_raw:
        sha = rb.get("sha", rb.get("commit_sha", ""))
        command = rb.get("command", f"git revert {sha}")
        # Ensure command format is correct
        if not command.startswith("git revert"):
            command = f"git revert {sha}"
        if sha:  # Only add if we have a SHA
            suggested_rollback.append(
                RollbackSuggestion(sha=sha, command=command)
            )

    # If no rollbacks but we have suspicious commits, generate rollback suggestions from them
    if not suggested_rollback and suspicious_commits:
        for commit in suspicious_commits:
            if commit.sha:
                suggested_rollback.append(
                    RollbackSuggestion(
                        sha=commit.sha,
                        command=f"git revert {commit.sha}",
                    )
                )

    return IncidentReport(
        timeWindow=time_window,
        timeline=timeline,
        suspiciousCommits=suspicious_commits,
        rootCause=root_cause,
        suggestedRollback=suggested_rollback,
        issues=issues or [],
    )
