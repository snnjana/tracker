"""Analysis engine that sends data to Groq for reasoning."""

import json
import re
from typing import Any, Dict, List

from groq import Groq, APIError, AuthenticationError, RateLimitError

from app.config import settings
from app.models import (
    CommitData,
    ErrorResponse,
    IssueData,
    LogEvent,
    MetricDataPoint,
    TimeWindow,
)

# Token budget - sized to accommodate code diffs
MAX_PROMPT_CHARS = 60000
PROMPT_OVERHEAD_CHARS = 3000


def _estimate_chars(obj: Any) -> int:
    """Estimate the character count of a serialized object."""
    return len(json.dumps(obj, default=str))


def _truncate_data(
    commits: List[CommitData],
    log_events: List[LogEvent],
    metric_data_points: List[MetricDataPoint],
    issues: List[IssueData],
) -> tuple[List[Dict], List[Dict], List[Dict], List[Dict]]:
    """Truncate data to fit within token budget.

    Strategy:
    1. Always preserve all commits (summarized).
    2. Always preserve issues (compact).
    3. Remove oldest log events first.
    4. If still over budget, remove oldest metric data points.
    """
    commits_data = []
    for c in commits:
        commit_info = {
            "sha": c.sha[:8],
            "author": c.author,
            "time": c.timestamp,
            "msg": c.message.split("\n")[0][:120],
            "files": len(c.changed_files),
            "key_files": c.changed_files[:5],
        }
        # Include patch/diff content for code-level analysis
        if c.patch:
            commit_info["diff"] = c.patch[:3000]
        commits_data.append(commit_info)

    issues_data = []
    for i in issues:
        issue_info = {
            "number": i.number,
            "title": i.title,
            "state": i.state,
            "created_at": i.created_at,
            "updated_at": i.updated_at,
            "labels": i.labels,
        }
        if i.body:
            issue_info["body"] = i.body[:300]
        issues_data.append(issue_info)

    logs_data = []
    for l in log_events:
        logs_data.append({
            "time": l.timestamp,
            "group": l.log_group.split("/")[-1],
            "msg": l.message[:200],
        })

    metrics_data = []
    for m in metric_data_points:
        metrics_data.append({
            "time": m.timestamp,
            "metric": m.metric_name,
            "val": m.value,
            "unit": m.unit,
        })

    available_chars = MAX_PROMPT_CHARS - PROMPT_OVERHEAD_CHARS
    commits_chars = _estimate_chars(commits_data)
    issues_chars = _estimate_chars(issues_data)
    remaining = available_chars - commits_chars - issues_chars

    metrics_chars = _estimate_chars(metrics_data)
    logs_chars = _estimate_chars(logs_data)

    if commits_chars + issues_chars + logs_chars + metrics_chars <= available_chars:
        return commits_data, logs_data, metrics_data, issues_data

    if metrics_chars <= remaining:
        remaining_for_logs = remaining - metrics_chars
        while logs_data and _estimate_chars(logs_data) > remaining_for_logs:
            logs_data.pop(0)
        return commits_data, logs_data, metrics_data, issues_data

    logs_data = []
    remaining_for_metrics = remaining
    while metrics_data and _estimate_chars(metrics_data) > remaining_for_metrics:
        metrics_data.pop(0)

    return commits_data, logs_data, metrics_data, issues_data


def _construct_prompt(
    commits_data: List[Dict],
    logs_data: List[Dict],
    metrics_data: List[Dict],
    issues_data: List[Dict],
    time_window: TimeWindow,
) -> str:
    """Construct a compact analysis prompt."""
    # Build commit strings with diff content included
    commit_parts = []
    for c in commits_data:
        header = f"- {c['sha']} | {c['time']} | {c['author']} | {c['msg']} | {c['files']} files ({', '.join(c.get('key_files', [])[:3])})"
        if c.get("diff"):
            header += f"\n  DIFF:\n  {c['diff'][:2000]}"
        commit_parts.append(header)

    commits_str = "\n".join(commit_parts)

    logs_str = "\n".join(
        f"- {l['time']} [{l['group']}] {l['msg']}"
        for l in logs_data[:50]
    )

    metrics_str = "\n".join(
        f"- {m['time']} {m['metric']}={m['val']}{m['unit']}"
        for m in metrics_data[:30]
    )

    issues_parts = []
    for i in issues_data:
        labels_str = ", ".join(i.get("labels", []))
        line = f"- #{i['number']} [{i['state']}] \"{i['title']}\" (labels: {labels_str}) - created {i['created_at']}"
        if i.get("body"):
            line += f"\n  Body: {i['body']}"
        issues_parts.append(line)
    issues_str = "\n".join(issues_parts)

    prompt = f"""Analyze this production incident. Time window: {time_window.start.isoformat()} to {time_window.end.isoformat()}

COMMITS (with code diffs):
{commits_str or "(none)"}

ISSUES:
{issues_str or "(none)"}

LOGS:
{logs_str or "(none)"}

METRICS:
{metrics_str or "(none)"}

Analyze the code changes in the diffs above. Identify which specific code changes are most likely to have caused the incident. Correlate GitHub issues with commits to understand the context. Explain what the code does and why it's problematic.

Respond with JSON only (no markdown, no code fences):
{{"timeline":[{{"timestamp":"...","type":"commit|log_event|metric_data_point","summary":"...","details":{{}}}}],"suspiciousCommits":[{{"sha":"full-40-char-sha","confidence":"High|Medium|Low","explanation":"detailed explanation referencing specific code changes from the diff"}}],"rootCause":"max 500 chars describing the specific code issue","suggestedRollbacks":[{{"sha":"full-sha","command":"git revert <sha>"}}]}}"""

    return prompt


async def analyze_incident(
    commits: List[CommitData],
    issues: List[IssueData],
    log_events: List[LogEvent],
    metric_data_points: List[MetricDataPoint],
    time_window: TimeWindow,
) -> Dict | ErrorResponse:
    """Send collected data to Groq for analysis.

    Uses the Groq API with the model specified in GROQ_MODEL.

    Returns:
        Parsed analysis result dict on success, or ErrorResponse on failure.
    """
    # Truncate data to fit token budget
    commits_data, logs_data, metrics_data, issues_data = _truncate_data(
        commits, log_events, metric_data_points, issues
    )

    # Construct prompt
    prompt = _construct_prompt(commits_data, logs_data, metrics_data, issues_data, time_window)

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)

        completion = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert SRE analyzing production incidents. Always respond with valid JSON only, no markdown formatting or code fences.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.1,
            max_completion_tokens=4096,
            top_p=1,
            stream=False,
        )

        text_response = completion.choices[0].message.content or ""

        # Parse JSON from response
        try:
            analysis_result = json.loads(text_response)
        except json.JSONDecodeError:
            # Try to extract JSON from possible markdown code fence
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text_response, re.DOTALL)
            if json_match:
                try:
                    analysis_result = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
                else:
                    return analysis_result

            # Try bare JSON object
            json_match = re.search(r"\{.*\}", text_response, re.DOTALL)
            if json_match:
                try:
                    analysis_result = json.loads(json_match.group())
                except json.JSONDecodeError:
                    return ErrorResponse(
                        code="PARSE_ERROR",
                        message="Failed to parse Groq response as JSON.",
                        details=text_response[:500],
                    )
            else:
                return ErrorResponse(
                    code="PARSE_ERROR",
                    message="Failed to parse Groq response as JSON.",
                    details=text_response[:500],
                )

        return analysis_result

    except AuthenticationError:
        return ErrorResponse(
            code="AUTH_ERROR",
            message="Invalid Groq API key. Check GROQ_API_KEY in your .env file.",
        )
    except RateLimitError as e:
        return ErrorResponse(
            code="RATE_LIMITED",
            message="Groq API rate limit exceeded. Please wait and try again.",
            details=str(e)[:300],
        )
    except APIError as e:
        error_msg = str(e)

        if "context" in error_msg.lower() or "token" in error_msg.lower():
            return ErrorResponse(
                code="CONTEXT_TOO_LARGE",
                message="The selected investigation duration is too large, or has too many tokens to be processed.",
                details="Try shortening the time window and try again.",
            )

        return ErrorResponse(
            code="API_ERROR",
            message=f"Groq API error: {error_msg[:200]}",
            details=str(e.status_code) if hasattr(e, "status_code") else None,
        )
    except Exception as e:
        return ErrorResponse(
            code="API_ERROR",
            message=f"Analysis could not be completed: {str(e)[:200]}",
        )
