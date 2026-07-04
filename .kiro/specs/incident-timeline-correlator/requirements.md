# Requirements Document

## Introduction

The AI Incident Timeline Correlator is a web application that helps engineers quickly identify the root cause of production incidents by correlating GitHub commit history and issues with AI-powered reasoning over a given time window. The user provides a GitHub repository URL, a time range (max 7 days), and optionally a GitHub token for private repo access. The tool fetches relevant commits (with code diffs) and issues, feeds them to Groq AI for reasoning, and produces a correlated timeline, suspicious commits, likely root cause analysis, and rollback suggestions.

## Glossary

- **Correlator**: The core backend system that orchestrates data fetching, analysis, and output generation for incident investigation.
- **Time_Window**: A start and end timestamp defining the period of interest for an incident investigation, limited to 7 days maximum.
- **Commit_Fetcher**: The component responsible for retrieving commit data and patch/diff content from the GitHub API within a specified time window.
- **Issue_Fetcher**: The component responsible for retrieving GitHub issues created or updated within a specified time window.
- **Analysis_Engine**: The component that sends collected data to Groq AI and processes the model's reasoning output.
- **Timeline**: A chronologically ordered sequence of events combining commits and observability signals within the time window.
- **Incident_Report**: The final output containing the timeline, suspicious commits, root cause analysis, rollback suggestions, and related issues.

## Requirements

### Requirement 1: Accept Investigation Input

**User Story:** As an engineer, I want to provide a GitHub repo URL, a time range, and optionally my GitHub token, so that the tool knows what data to gather for my incident investigation.

#### Acceptance Criteria

1. WHEN a user provides a GitHub repository URL and a time range with start and end timestamps in ISO 8601 format, THE Correlator SHALL validate that the URL matches the pattern `https://github.com/{owner}/{repo}` and confirm the start time is earlier than the end time.
2. IF the GitHub repository URL does not match the expected pattern `https://github.com/{owner}/{repo}`, THEN THE Correlator SHALL return an error indicating the URL format is invalid.
3. IF the time range start time is equal to or later than the end time, THEN THE Correlator SHALL return an error indicating an invalid time range.
4. IF the user does not provide a time range alongside the GitHub repository URL, THEN THE Correlator SHALL return an error indicating that a time range is required.
5. WHEN the Time_Window duration exceeds 168 hours (7 days), THE Correlator SHALL return an error indicating the time range exceeds the maximum allowed duration.
6. WHEN a user provides a GitHub token in the request, THE Correlator SHALL use that token for all GitHub API calls for that request. The token SHALL NOT be stored on the server beyond the request lifecycle.
7. IF no GitHub token is provided by the user, THE Correlator SHALL fall back to the server-configured token if available, or proceed without authentication (with reduced rate limits).

### Requirement 2: Fetch GitHub Commits

**User Story:** As an engineer, I want the tool to pull recent commits with their code diffs from the specified repository within the investigation window, so that I can see what code changes happened around the time of the incident.

#### Acceptance Criteria

1. WHEN a valid Time_Window is established, THE Commit_Fetcher SHALL retrieve commits from the default branch of the GitHub repository that fall within the Time_Window using the GitHub API, up to a maximum of 250 commits.
2. THE Commit_Fetcher SHALL include for each commit: the full 40-character SHA, author name, author email, timestamp in ISO 8601 format, commit message up to 72,000 characters, list of changed files up to 3,000 files, and patch/diff content (truncated to 2,000 characters per file, 8,000 total per commit).
3. IF the GitHub API returns an authentication error, THEN THE Commit_Fetcher SHALL return an error immediately indicating that valid GitHub credentials are required.
4. IF the GitHub API returns a rate-limit response, THEN THE Commit_Fetcher SHALL return an error immediately indicating the rate limit has been exceeded and suggesting the user provide a GitHub token.
5. IF no commits exist within the Time_Window, THEN THE Commit_Fetcher SHALL return an empty commit list.
6. IF the GitHub API is unreachable or returns a server error, THEN THE Commit_Fetcher SHALL return an error immediately (no retries) indicating the GitHub API is unavailable.

### Requirement 3: Fetch GitHub Issues

**User Story:** As an engineer, I want the tool to pull GitHub issues created or updated within the investigation window, so that I can correlate reported problems with code changes.

#### Acceptance Criteria

1. WHEN a valid Time_Window is established, THE Issue_Fetcher SHALL retrieve up to 50 GitHub issues (open and closed) that were created or updated within the Time_Window.
2. THE Issue_Fetcher SHALL include for each issue: the issue number, title, state (open/closed), created_at timestamp, updated_at timestamp, labels, body (truncated to 500 characters), and HTML URL.
3. IF the GitHub API returns an authentication or rate-limit error, THEN THE Issue_Fetcher SHALL return an error immediately (no retries).
4. IF no issues exist within the Time_Window, THEN THE Issue_Fetcher SHALL return an empty issue list.

### Requirement 4: Correlate Data Using Groq AI

**User Story:** As an engineer, I want the tool to feed commit history, code diffs, and issues data to an AI model for joint reasoning, so that I can get an intelligent analysis of the incident.

#### Acceptance Criteria

1. WHEN commits and issues have been successfully fetched, THE Analysis_Engine SHALL construct a prompt containing both datasets and send the prompt to Groq AI.
2. THE Analysis_Engine SHALL include in the prompt: the commit list with diff content, the issues list, and the Time_Window boundaries.
3. IF the Groq API returns an error, THEN THE Analysis_Engine SHALL return a descriptive error indicating the analysis could not be completed.
4. IF the Groq API returns an authentication error, THEN THE Analysis_Engine SHALL return an error indicating that a valid GROQ_API_KEY is required.
5. IF the combined data exceeds the configured token limit (60,000 characters), THEN THE Analysis_Engine SHALL truncate data while preserving all commits and issues, removing oldest log events first, then oldest metric data points.
6. IF the Groq API returns a rate-limit error, THEN THE Analysis_Engine SHALL return an error indicating the rate limit has been exceeded.

### Requirement 5: Generate Incident Report

**User Story:** As an engineer, I want the tool to produce a structured incident report with a timeline, suspicious commits, root cause, and rollback suggestions, so that I can act on the findings quickly.

#### Acceptance Criteria

1. WHEN the Analysis_Engine receives a successful response from Groq AI, THE Correlator SHALL produce an Incident_Report.
2. THE Incident_Report SHALL contain a Timeline listing events ordered chronologically by timestamp, with events sharing identical timestamps ordered commits-first then log events then metric data points.
3. THE Incident_Report SHALL identify the most suspicious commit or commits, each with a confidence score expressed as High, Medium, or Low, and an explanation referencing specific code changes from the diff.
4. THE Incident_Report SHALL include a root cause summary of no more than 500 characters derived from the AI reasoning.
5. THE Incident_Report SHALL include a suggested rollback section specifying which commit SHA(s) to revert and the corresponding git revert command(s) for each. IF no explicit rollbacks are returned by the AI but suspicious commits are identified, THEN rollback commands SHALL be auto-generated from the suspicious commits.
6. THE Incident_Report SHALL include a list of related GitHub issues fetched within the time window.
7. THE Correlator SHALL format the Incident_Report in a structured JSON format that includes clearly labeled sections for Timeline, Suspicious Commits, Root Cause, Suggested Rollback, and Issues.
8. THE Report Generator SHALL handle variant key names from the AI response (camelCase, snake_case) and map them to the canonical schema.
9. THE Report Generator SHALL sanitize invalid timeline entry types returned by the AI, inferring the correct type from entry content or defaulting to log_event.

### Requirement 6: Serialize and Parse Incident Report

**User Story:** As an engineer, I want to export and re-import incident reports in a structured data format, so that I can store them, share them, and load them into other tools.

#### Acceptance Criteria

1. THE Correlator SHALL serialize the Incident_Report into a JSON format that includes all Incident_Report sections: Timeline, Suspicious Commits, Root Cause, Suggested Rollback, and Issues.
2. WHEN a JSON-formatted Incident_Report is provided, THE Correlator SHALL parse the JSON back into an Incident_Report object.
3. THE Correlator SHALL ensure that serializing a valid Incident_Report to JSON and then parsing the resulting JSON back produces an equivalent Incident_Report object.
4. IF the provided JSON does not conform to the Incident_Report schema, THEN THE Correlator SHALL return a descriptive error.
5. IF the provided input is not syntactically valid JSON, THEN THE Correlator SHALL return an error indicating that the input could not be parsed as JSON.
