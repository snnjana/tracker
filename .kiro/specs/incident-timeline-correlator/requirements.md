# Requirements Document

## Introduction

The AI Incident Timeline Correlator is a tool that helps engineers quickly identify the root cause of production incidents by correlating GitHub commit history with AWS CloudWatch logs and metrics over a given time window. The user provides a GitHub repository URL and either a time range or a CloudWatch alarm reference. The tool fetches relevant commits and observability data, feeds them to Amazon Bedrock Claude for reasoning, and produces a correlated timeline, suspicious commits, likely root cause analysis, and rollback suggestions.

## Glossary

- **Correlator**: The core system that orchestrates data fetching, analysis, and output generation for incident investigation.
- **Time_Window**: A start and end timestamp defining the period of interest for an incident investigation.
- **Commit_Fetcher**: The component responsible for retrieving commit data from the GitHub API within a specified time window.
- **Log_Fetcher**: The component responsible for retrieving CloudWatch logs and metrics within a specified time window.
- **Analysis_Engine**: The component that sends collected data to Amazon Bedrock Claude and processes the model's reasoning output.
- **Timeline**: A chronologically ordered sequence of events combining commits and observability signals within the time window.
- **Incident_Report**: The final output containing the timeline, suspicious commits, root cause analysis, and rollback suggestions.
- **CloudWatch_Alarm**: An AWS CloudWatch alarm that can be used as an alternative to a manual time range to define the investigation window.

## Requirements

### Requirement 1: Accept Investigation Input

**User Story:** As an engineer, I want to provide a GitHub repo URL and a time range or CloudWatch alarm, so that the tool knows what data to gather for my incident investigation.

#### Acceptance Criteria

1. WHEN a user provides a GitHub repository URL and a time range with start and end timestamps in ISO 8601 format, THE Correlator SHALL validate that the URL matches the pattern `https://github.com/{owner}/{repo}` and confirm the start time is earlier than the end time.
2. WHEN a user provides a GitHub repository URL and a CloudWatch alarm ARN, THE Correlator SHALL resolve the most recent ALARM state-change timestamp as the Time_Window end and the most recent preceding OK-to-ALARM transition timestamp as the Time_Window start.
3. IF the GitHub repository URL does not match the expected pattern `https://github.com/{owner}/{repo}`, THEN THE Correlator SHALL return an error indicating the URL format is invalid.
4. IF the time range start time is equal to or later than the end time, THEN THE Correlator SHALL return an error indicating an invalid time range.
5. IF the CloudWatch alarm ARN is invalid or the alarm cannot be found, THEN THE Correlator SHALL return an error indicating the alarm could not be resolved.
6. IF the user does not provide either a time range or a CloudWatch alarm ARN alongside the GitHub repository URL, THEN THE Correlator SHALL return an error indicating that either a time range or a CloudWatch alarm ARN is required.
7. WHEN the Time_Window duration exceeds 72 hours, THE Correlator SHALL return an error indicating the time range exceeds the maximum allowed duration of 72 hours.

### Requirement 2: Fetch GitHub Commits

**User Story:** As an engineer, I want the tool to pull recent commits from the specified repository within the investigation window, so that I can see what code changes happened around the time of the incident.

#### Acceptance Criteria

1. WHEN a valid Time_Window is established, THE Commit_Fetcher SHALL retrieve commits from the default branch of the GitHub repository that fall within the Time_Window using the GitHub API, up to a maximum of 250 commits.
2. THE Commit_Fetcher SHALL include for each commit: the full 40-character SHA, author name, author email, timestamp in ISO 8601 format, commit message up to 72,000 characters, and list of changed files up to 3,000 files.
3. IF the GitHub API returns an authentication error, THEN THE Commit_Fetcher SHALL return an error indicating that valid GitHub credentials are required.
4. IF the GitHub API returns a rate-limit response, THEN THE Commit_Fetcher SHALL return an error indicating the rate limit has been exceeded and include the reset time.
5. IF no commits exist within the Time_Window, THEN THE Commit_Fetcher SHALL return an empty commit list and a warning indicating no commits were found in the specified window.
6. IF the GitHub API is unreachable or returns a server error, THEN THE Commit_Fetcher SHALL retry the request up to 3 times with exponential backoff and, if all attempts fail, return an error indicating the GitHub API is unavailable.

### Requirement 3: Fetch CloudWatch Logs and Metrics

**User Story:** As an engineer, I want the tool to pull CloudWatch logs and metrics for the investigation window, so that I can see what operational signals occurred around the time of the incident.

#### Acceptance Criteria

1. WHEN a valid Time_Window is established, THE Log_Fetcher SHALL retrieve up to 10,000 CloudWatch log events from the specified log groups that fall within the Time_Window, ordered by timestamp ascending.
2. WHEN a valid Time_Window is established, THE Log_Fetcher SHALL retrieve CloudWatch metric data points for the specified metrics that fall within the Time_Window using a period of 60 seconds.
3. THE Log_Fetcher SHALL include for each log event: the timestamp, log group name, log stream name, and message content truncated to 4,000 characters.
4. THE Log_Fetcher SHALL include for each metric data point: the timestamp, metric name, namespace, value, and unit.
5. IF the AWS credentials are missing or invalid, THEN THE Log_Fetcher SHALL return an error indicating that valid AWS credentials are required.
6. IF a specified log group does not exist, THEN THE Log_Fetcher SHALL return an error identifying the missing log group.
7. IF a specified metric does not exist in the given namespace, THEN THE Log_Fetcher SHALL return an error identifying the missing metric and namespace.
8. IF no log events or metric data points are found within the Time_Window, THEN THE Log_Fetcher SHALL return an empty collection for the respective data type and a warning indicating no data was found in the specified window.
9. IF the CloudWatch API returns a throttling error, THEN THE Log_Fetcher SHALL retry the request up to 3 times with exponential backoff and return an error indicating the API rate limit was exceeded if all retries fail.

### Requirement 4: Correlate Data Using Bedrock Claude

**User Story:** As an engineer, I want the tool to feed both commit history and observability data to an AI model for joint reasoning, so that I can get an intelligent analysis of the incident.

#### Acceptance Criteria

1. WHEN commits and CloudWatch data have been successfully fetched, THE Analysis_Engine SHALL construct a prompt containing both datasets and send the prompt to Amazon Bedrock Claude within 60 seconds.
2. THE Analysis_Engine SHALL include in the prompt: the full commit list, the CloudWatch log events, the CloudWatch metric data points, and the Time_Window boundaries.
3. IF the Bedrock API returns an error, THEN THE Analysis_Engine SHALL return a descriptive error indicating the analysis could not be completed and include the Bedrock error details.
4. IF the Bedrock API returns an authentication or authorization error, THEN THE Analysis_Engine SHALL return an error indicating that valid AWS credentials with Bedrock invoke permissions are required.
5. IF the combined data exceeds the configured Bedrock Claude context window token limit, THEN THE Analysis_Engine SHALL truncate the oldest log events first while preserving all commits and metric data points.
6. IF the combined data still exceeds the context window token limit after all log events have been removed, THEN THE Analysis_Engine SHALL truncate the oldest metric data points until the prompt fits within the limit while preserving all commits.
7. IF the Bedrock API does not respond within 60 seconds, THEN THE Analysis_Engine SHALL return an error indicating the analysis request timed out.

### Requirement 5: Generate Incident Report

**User Story:** As an engineer, I want the tool to produce a structured incident report with a timeline, suspicious commits, root cause, and rollback suggestions, so that I can act on the findings quickly.

#### Acceptance Criteria

1. WHEN the Analysis_Engine receives a successful response from Bedrock Claude, THE Correlator SHALL produce an Incident_Report within 5 seconds of receiving the response.
2. THE Incident_Report SHALL contain a Timeline listing all commits and all CloudWatch log events and metric data points that the Analysis_Engine identified as anomalous or correlated with the incident, ordered chronologically by timestamp, with events sharing identical timestamps ordered commits-first then log events then metric data points.
3. THE Incident_Report SHALL identify the most suspicious commit or commits, each with a confidence score expressed as High, Medium, or Low, and an explanation of why the commit is suspicious based on its temporal proximity to observability anomalies and the nature of its changes.
4. THE Incident_Report SHALL include a root cause summary of no more than 500 characters derived from the AI reasoning, describing the most likely cause of the incident.
5. THE Incident_Report SHALL include a suggested rollback section specifying which commit SHA(s) to revert and the corresponding git revert command(s) for each.
6. THE Correlator SHALL format the Incident_Report in a structured format that includes clearly labeled sections for Timeline, Suspicious Commits, Root Cause, and Suggested Rollback.
7. IF the Analysis_Engine response does not identify any suspicious commits, THEN THE Correlator SHALL produce an Incident_Report with an empty Suspicious Commits section and a note indicating that no commits were identified as suspicious within the Time_Window.

### Requirement 6: Serialize and Parse Incident Report

**User Story:** As an engineer, I want to export and re-import incident reports in a structured data format, so that I can store them, share them, and load them into other tools.

#### Acceptance Criteria

1. THE Correlator SHALL serialize the Incident_Report into a JSON format that includes all Incident_Report sections: Timeline, Suspicious Commits, Root Cause, and Suggested Rollback.
2. WHEN a JSON-formatted Incident_Report is provided, THE Correlator SHALL parse the JSON back into an Incident_Report object within 5 seconds for inputs up to 10 MB in size.
3. THE Correlator SHALL ensure that serializing a valid Incident_Report to JSON and then parsing the resulting JSON back produces an Incident_Report object with field-by-field equality across all sections compared to the original.
4. IF the provided JSON does not conform to the Incident_Report schema, THEN THE Correlator SHALL return an error indicating each field that is invalid or missing.
5. IF the provided input is not syntactically valid JSON, THEN THE Correlator SHALL return an error indicating that the input could not be parsed as JSON.
