"""Transforms Bedrock analysis response into a structured IncidentReport."""

from typing import Any, Dict, List

from app.models import (
    IncidentReport,
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
    analysis_result: Dict[str, Any], time_window: TimeWindow
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

    # Parse suspicious commits
    suspicious_raw = analysis_result.get("suspiciousCommits", [])
    suspicious_commits: List[SuspiciousCommit] = []
    for commit in suspicious_raw:
        confidence = commit.get("confidence", "Low")
        if confidence not in ("High", "Medium", "Low"):
            confidence = "Low"
        suspicious_commits.append(
            SuspiciousCommit(
                sha=commit.get("sha", ""),
                confidence=confidence,
                explanation=commit.get("explanation", ""),
            )
        )

    # Parse root cause (truncate to 500 chars)
    root_cause = analysis_result.get("rootCause", "No root cause identified.")
    if len(root_cause) > MAX_ROOT_CAUSE_LENGTH:
        root_cause = root_cause[:MAX_ROOT_CAUSE_LENGTH]

    # Parse rollback suggestions
    rollbacks_raw = analysis_result.get("suggestedRollbacks", [])
    suggested_rollback: List[RollbackSuggestion] = []
    for rb in rollbacks_raw:
        sha = rb.get("sha", "")
        command = rb.get("command", f"git revert {sha}")
        # Ensure command format is correct
        if not command.startswith("git revert"):
            command = f"git revert {sha}"
        suggested_rollback.append(
            RollbackSuggestion(sha=sha, command=command)
        )

    return IncidentReport(
        timeWindow=time_window,
        timeline=timeline,
        suspiciousCommits=suspicious_commits,
        rootCause=root_cause,
        suggestedRollback=suggested_rollback,
    )
