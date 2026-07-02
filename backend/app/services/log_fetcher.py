"""Fetches CloudWatch logs and metrics within the investigation time window."""

import os
from datetime import datetime, timezone
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from app.config import settings
from app.models import (
    ErrorResponse,
    LogEvent,
    MetricDataPoint,
    MetricQuery,
    TimeWindow,
)
from app.utils.retry import async_retry

MAX_LOG_EVENTS = 10000
MAX_MESSAGE_LENGTH = 4000
METRIC_PERIOD_SECONDS = 60


class CloudWatchThrottleError(Exception):
    """Raised for retryable CloudWatch throttling errors."""

    pass


@async_retry(
    max_attempts=3,
    base_delay=1.0,
    max_delay=10.0,
    multiplier=2.0,
    retryable_exceptions=(CloudWatchThrottleError,),
)
async def fetch_logs(
    log_group_names: List[str], time_window: TimeWindow
) -> List[LogEvent] | ErrorResponse:
    """Fetch CloudWatch log events within the time window.

    Args:
        log_group_names: List of CloudWatch log group names to query.
        time_window: The investigation time window.

    Returns:
        List of LogEvent on success, or ErrorResponse on failure.
    """
    if not log_group_names:
        return []

    try:
        client = boto3.client("logs", **settings.get_boto3_kwargs())
        all_events: List[LogEvent] = []

        start_ms = int(time_window.start.timestamp() * 1000)
        end_ms = int(time_window.end.timestamp() * 1000)

        for log_group in log_group_names:
            try:
                # Check if log group exists
                response = client.describe_log_groups(
                    logGroupNamePrefix=log_group, limit=1
                )
                groups = response.get("logGroups", [])
                if not any(g["logGroupName"] == log_group for g in groups):
                    return ErrorResponse(
                        code="LOG_GROUP_NOT_FOUND",
                        message=f"Log group not found: {log_group}",
                    )

                # Fetch log events
                paginator = client.get_paginator("filter_log_events")
                page_iterator = paginator.paginate(
                    logGroupName=log_group,
                    startTime=start_ms,
                    endTime=end_ms,
                    limit=MAX_LOG_EVENTS - len(all_events),
                )

                for page in page_iterator:
                    for event in page.get("events", []):
                        if len(all_events) >= MAX_LOG_EVENTS:
                            break

                        message = event.get("message", "")
                        if len(message) > MAX_MESSAGE_LENGTH:
                            message = message[:MAX_MESSAGE_LENGTH]

                        log_event = LogEvent(
                            timestamp=datetime.fromtimestamp(
                                event["timestamp"] / 1000, tz=timezone.utc
                            ).isoformat(),
                            logGroup=log_group,
                            logStream=event.get("logStreamName", ""),
                            message=message,
                        )
                        all_events.append(log_event)

                    if len(all_events) >= MAX_LOG_EVENTS:
                        break

            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                if error_code == "ThrottlingException":
                    raise CloudWatchThrottleError(
                        "CloudWatch API rate limit exceeded"
                    )
                elif error_code == "ResourceNotFoundException":
                    return ErrorResponse(
                        code="LOG_GROUP_NOT_FOUND",
                        message=f"Log group not found: {log_group}",
                    )
                raise

            if len(all_events) >= MAX_LOG_EVENTS:
                break

        # Sort by timestamp ascending
        all_events.sort(key=lambda e: e.timestamp)
        return all_events

    except NoCredentialsError:
        return ErrorResponse(
            code="AWS_AUTH_ERROR",
            message="Valid AWS credentials are required to fetch CloudWatch logs.",
        )
    except CloudWatchThrottleError:
        raise
    except ClientError as e:
        return ErrorResponse(
            code="API_UNAVAILABLE",
            message=f"CloudWatch API error: {e.response['Error']['Message']}",
        )
    except Exception as e:
        return ErrorResponse(
            code="API_UNAVAILABLE",
            message=f"Failed to fetch CloudWatch logs: {str(e)}",
        )


@async_retry(
    max_attempts=3,
    base_delay=1.0,
    max_delay=10.0,
    multiplier=2.0,
    retryable_exceptions=(CloudWatchThrottleError,),
)
async def fetch_metrics(
    metric_queries: List[MetricQuery], time_window: TimeWindow
) -> List[MetricDataPoint] | ErrorResponse:
    """Fetch CloudWatch metric data points within the time window.

    Args:
        metric_queries: List of metric queries to execute.
        time_window: The investigation time window.

    Returns:
        List of MetricDataPoint on success, or ErrorResponse on failure.
    """
    if not metric_queries:
        return []

    try:
        client = boto3.client("cloudwatch", **settings.get_boto3_kwargs())
        all_data_points: List[MetricDataPoint] = []

        for query in metric_queries:
            try:
                dimensions = []
                if query.dimensions:
                    dimensions = [
                        {"Name": k, "Value": v}
                        for k, v in query.dimensions.items()
                    ]

                response = client.get_metric_statistics(
                    Namespace=query.namespace,
                    MetricName=query.metric_name,
                    StartTime=time_window.start,
                    EndTime=time_window.end,
                    Period=METRIC_PERIOD_SECONDS,
                    Statistics=["Average", "Maximum", "Minimum"],
                    Dimensions=dimensions,
                )

                datapoints = response.get("Datapoints", [])

                for dp in datapoints:
                    # Use Average as the primary value
                    value = dp.get("Average", dp.get("Maximum", dp.get("Minimum", 0)))
                    unit = dp.get("Unit", "None")
                    timestamp = dp.get("Timestamp")

                    if isinstance(timestamp, datetime):
                        ts_str = timestamp.isoformat()
                    else:
                        ts_str = str(timestamp)

                    data_point = MetricDataPoint(
                        timestamp=ts_str,
                        metricName=query.metric_name,
                        namespace=query.namespace,
                        value=value,
                        unit=unit,
                    )
                    all_data_points.append(data_point)

            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                if error_code == "ThrottlingException":
                    raise CloudWatchThrottleError(
                        "CloudWatch API rate limit exceeded"
                    )
                elif error_code in ("InvalidParameterValue", "MissingParameter"):
                    return ErrorResponse(
                        code="METRIC_NOT_FOUND",
                        message=f"Metric not found: {query.metric_name} in namespace {query.namespace}",
                    )
                raise

        # Sort by timestamp ascending
        all_data_points.sort(key=lambda dp: dp.timestamp)
        return all_data_points

    except NoCredentialsError:
        return ErrorResponse(
            code="AWS_AUTH_ERROR",
            message="Valid AWS credentials are required to fetch CloudWatch metrics.",
        )
    except CloudWatchThrottleError:
        raise
    except ClientError as e:
        return ErrorResponse(
            code="API_UNAVAILABLE",
            message=f"CloudWatch API error: {e.response['Error']['Message']}",
        )
    except Exception as e:
        return ErrorResponse(
            code="API_UNAVAILABLE",
            message=f"Failed to fetch CloudWatch metrics: {str(e)}",
        )
