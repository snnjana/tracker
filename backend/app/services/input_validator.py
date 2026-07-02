"""Input validation service for investigation requests."""

import re
from datetime import datetime, timedelta, timezone
from typing import Tuple

from app.models import ErrorResponse, InvestigationInput, TimeWindow

GITHUB_URL_PATTERN = re.compile(
    r"^https://github\.com/([a-zA-Z0-9\-_.]+)/([a-zA-Z0-9\-_.]+)/?$"
)
MAX_DURATION_HOURS = 168  # 1 week


def validate_investigation_input(
    input_data: InvestigationInput,
) -> Tuple[str, str, TimeWindow] | ErrorResponse:
    """Validate the investigation input and extract owner/repo and time window.

    Returns:
        Tuple of (owner, repo, TimeWindow) on success, or ErrorResponse on failure.
    """
    # Validate GitHub URL
    match = GITHUB_URL_PATTERN.match(input_data.repo_url)
    if not match:
        return ErrorResponse(
            code="INVALID_URL",
            message="GitHub repository URL must match the pattern https://github.com/{owner}/{repo}",
        )

    owner = match.group(1)
    repo = match.group(2)

    # Validate time range is provided
    if input_data.time_range is None:
        return ErrorResponse(
            code="MISSING_TIME_SOURCE",
            message="A time range is required.",
        )

    # Validate time range
    try:
        start = datetime.fromisoformat(
            input_data.time_range.start.replace("Z", "+00:00")
        )
        end = datetime.fromisoformat(
            input_data.time_range.end.replace("Z", "+00:00")
        )
    except (ValueError, TypeError) as e:
        return ErrorResponse(
            code="INVALID_TIME_RANGE",
            message=f"Invalid ISO 8601 timestamp format: {e}",
        )

    if start >= end:
        return ErrorResponse(
            code="INVALID_TIME_RANGE",
            message="Time range start must be earlier than end.",
        )

    duration = end - start
    if duration > timedelta(hours=MAX_DURATION_HOURS):
        return ErrorResponse(
            code="TIME_RANGE_EXCEEDS_MAX",
            message=f"Time range exceeds the maximum allowed duration of {MAX_DURATION_HOURS} hours (1 week).",
        )

    time_window = TimeWindow(start=start, end=end)
    return (owner, repo, time_window)
