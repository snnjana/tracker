"""Investigation endpoint router."""

import asyncio
from typing import List

from fastapi import APIRouter, HTTPException

from app.models import (
    CommitData,
    ErrorResponse,
    IncidentReport,
    InvestigationInput,
    LogEvent,
    MetricDataPoint,
    TimeWindow,
)
from app.services.analysis_engine import analyze_incident
from app.services.commit_fetcher import fetch_commits
from app.services.input_validator import validate_investigation_input
from app.services.log_fetcher import fetch_logs, fetch_metrics
from app.services.report_generator import generate_report

router = APIRouter()


@router.post("/api/investigate", response_model=IncidentReport)
async def investigate(input_data: InvestigationInput):
    """Run an incident investigation.

    Validates input, fetches data from GitHub and CloudWatch,
    analyzes with Groq, and returns a structured incident report.
    """
    # Step 1: Validate input
    validation_result = validate_investigation_input(input_data)

    if isinstance(validation_result, ErrorResponse):
        raise HTTPException(
            status_code=400,
            detail=validation_result.model_dump(),
        )

    owner, repo, time_window = validation_result

    # Step 2: Fetch data in parallel
    log_group_names = input_data.log_group_names or []
    metric_queries = input_data.metric_queries or []

    commits_task = fetch_commits(owner, repo, time_window)
    logs_task = fetch_logs(log_group_names, time_window)
    metrics_task = fetch_metrics(metric_queries, time_window)

    commits_result, logs_result, metrics_result = await asyncio.gather(
        commits_task, logs_task, metrics_task
    )

    # Check for errors in fetch results
    if isinstance(commits_result, ErrorResponse):
        raise HTTPException(
            status_code=502,
            detail=commits_result.model_dump(),
        )

    if isinstance(logs_result, ErrorResponse):
        raise HTTPException(
            status_code=502,
            detail=logs_result.model_dump(),
        )

    if isinstance(metrics_result, ErrorResponse):
        raise HTTPException(
            status_code=502,
            detail=metrics_result.model_dump(),
        )

    commits: List[CommitData] = commits_result
    log_events: List[LogEvent] = logs_result
    metric_data_points: List[MetricDataPoint] = metrics_result

    # Step 3: Analyze with Groq
    analysis_result = await analyze_incident(
        commits=commits,
        log_events=log_events,
        metric_data_points=metric_data_points,
        time_window=time_window,
    )

    if isinstance(analysis_result, ErrorResponse):
        raise HTTPException(
            status_code=502,
            detail=analysis_result.model_dump(),
        )

    # Step 4: Generate report
    report = generate_report(analysis_result, time_window)

    return report
