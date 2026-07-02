# Implementation Plan: Incident Timeline Correlator

## Overview

This plan implements a TypeScript/Node.js CLI tool that correlates GitHub commit history with AWS CloudWatch observability data using Amazon Bedrock Claude for root cause analysis. The implementation follows a pipeline architecture: Input Validation → Data Fetching (parallel) → Analysis → Report Generation. Each stage is built as a discrete, testable component with typed interfaces using discriminated union Result types.

## Tasks

- [ ] 1. Set up project structure and core types
  - [ ] 1.1 Initialize TypeScript project with Vitest and fast-check
    - Create `package.json` with dependencies: `@aws-sdk/client-cloudwatch-logs`, `@aws-sdk/client-cloudwatch`, `@aws-sdk/client-bedrock-runtime`, `@octokit/rest`, `fast-check`, `vitest`
    - Create `tsconfig.json` with strict mode enabled
    - Create `vitest.config.ts`
    - Create directory structure: `src/`, `src/types/`, `src/components/`, `src/utils/`, `tests/`
    - _Requirements: All_

  - [ ] 1.2 Define core type definitions and interfaces
    - Create `src/types/index.ts` with all interfaces: `InvestigationInput`, `ValidatedInput`, `TimeWindow`, `ValidationError`, `ValidationResult`, `CommitData`, `CommitList`, `LogEvent`, `LogEventList`, `MetricDataPoint`, `MetricDataList`, `MetricQuery`, `AnalysisInput`, `AnalysisOutput`, `TimelineEntry`, `SuspiciousCommit`, `RollbackSuggestion`, `IncidentReport`, `TokenBudget`
    - Create `src/types/errors.ts` with error types: `FetchError`, `ResolverError`, `AnalysisError`, `ParseError`, `FieldError`
    - Create `src/types/result.ts` with the generic `Result<T, E>` discriminated union type
    - _Requirements: 1.1, 2.2, 3.3, 3.4, 5.2, 5.3, 5.4, 5.5, 6.1_

- [ ] 2. Implement Input Validation
  - [ ] 2.1 Implement InputValidator component
    - Create `src/components/input-validator.ts`
    - Implement GitHub URL validation against pattern `https://github.com/{owner}/{repo}`
    - Implement time range validation (start < end, duration ≤ 72 hours)
    - Implement alarm ARN format validation
    - Implement check that either time range or alarm ARN is provided
    - Return typed `ValidationResult` with specific error codes
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [ ]* 2.2 Write property test for GitHub URL validation
    - **Property 1: GitHub URL Validation**
    - **Validates: Requirements 1.1, 1.3**

  - [ ]* 2.3 Write property test for time range validation
    - **Property 2: Time Range Validation**
    - **Validates: Requirements 1.4, 1.7**

  - [ ]* 2.4 Write unit tests for InputValidator
    - Test missing time source returns MISSING_TIME_SOURCE error
    - Test invalid alarm ARN returns INVALID_ALARM error
    - Test valid inputs pass validation
    - _Requirements: 1.5, 1.6_

- [ ] 3. Implement Time Window Resolution
  - [ ] 3.1 Implement TimeWindowResolver component
    - Create `src/components/time-window-resolver.ts`
    - Implement alarm ARN parsing and validation
    - Implement CloudWatch DescribeAlarmHistory call to resolve ALARM state-change timestamps
    - Map OK-to-ALARM transition to start, most recent ALARM state to end
    - Return `Result<TimeWindow, ResolverError>` with typed errors
    - _Requirements: 1.2, 1.5_

  - [ ]* 3.2 Write unit tests for TimeWindowResolver
    - Test successful alarm resolution with mocked CloudWatch client
    - Test alarm not found returns ALARM_NOT_FOUND error
    - Test invalid ARN returns INVALID_ARN error
    - Test AWS auth error returns AWS_AUTH_ERROR
    - _Requirements: 1.2, 1.5_

- [ ] 4. Checkpoint - Validate input layer
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement GitHub Commit Fetching
  - [ ] 5.1 Implement CommitFetcher component
    - Create `src/components/commit-fetcher.ts`
    - Implement GitHub API call using Octokit to list commits within TimeWindow on default branch
    - Map API response to `CommitData` objects (SHA, author, email, timestamp, message truncated to 72,000 chars, changed files truncated to 3,000)
    - Limit to 250 commits maximum
    - Return empty list with warning if no commits found
    - _Requirements: 2.1, 2.2, 2.5_

  - [ ] 5.2 Implement retry logic utility
    - Create `src/utils/retry.ts`
    - Implement exponential backoff retry with configurable max attempts (3), base delay (1000ms), max delay (10000ms), and backoff multiplier (2)
    - Only retry on transient errors (5xx, throttling); never retry auth/validation/not-found errors
    - _Requirements: 2.6, 3.9_

  - [ ] 5.3 Integrate retry logic into CommitFetcher
    - Wrap GitHub API calls with retry utility
    - Map GitHub API errors to typed `FetchError` codes: AUTH_ERROR, RATE_LIMITED, API_UNAVAILABLE
    - Include rate limit reset time in RATE_LIMITED errors
    - _Requirements: 2.3, 2.4, 2.6_

  - [ ]* 5.4 Write property test for commit data mapping
    - **Property 3: Commit Data Mapping**
    - **Validates: Requirements 2.2**

  - [ ]* 5.5 Write unit tests for CommitFetcher
    - Test auth error returns AUTH_ERROR
    - Test rate limit returns RATE_LIMITED with reset time
    - Test empty commits returns warning
    - Test retry logic executes 3 times with backoff
    - _Requirements: 2.3, 2.4, 2.5, 2.6_

- [ ] 6. Implement CloudWatch Log and Metric Fetching
  - [ ] 6.1 Implement LogFetcher component
    - Create `src/components/log-fetcher.ts`
    - Implement CloudWatch Logs API call to fetch up to 10,000 log events from specified log groups within TimeWindow, ordered by timestamp ascending
    - Map log events to `LogEvent` objects with message truncated to 4,000 characters
    - Implement CloudWatch Metrics API call to fetch metric data points for specified metrics within TimeWindow using 60-second period
    - Map metric data to `MetricDataPoint` objects
    - Return empty collections with warnings when no data found
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.8_

  - [ ] 6.2 Integrate retry logic and error handling into LogFetcher
    - Wrap CloudWatch API calls with retry utility
    - Map AWS errors to typed `FetchError` codes: AWS_AUTH_ERROR, LOG_GROUP_NOT_FOUND, METRIC_NOT_FOUND, THROTTLED, API_UNAVAILABLE
    - Include specific log group or metric name in error details
    - _Requirements: 3.5, 3.6, 3.7, 3.9_

  - [ ]* 6.3 Write property test for log event mapping and truncation
    - **Property 4: Log Event Mapping and Truncation**
    - **Validates: Requirements 3.3**

  - [ ]* 6.4 Write property test for metric data point mapping
    - **Property 5: Metric Data Point Mapping**
    - **Validates: Requirements 3.4**

  - [ ]* 6.5 Write unit tests for LogFetcher
    - Test AWS auth error returns proper error
    - Test missing log group identified in error
    - Test missing metric identified in error
    - Test empty results include warning
    - Test retry logic on throttling
    - _Requirements: 3.5, 3.6, 3.7, 3.8, 3.9_

- [ ] 7. Checkpoint - Validate data fetching layer
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement Analysis Engine
  - [ ] 8.1 Implement token budget management and truncation logic
    - Create `src/components/analysis-engine.ts`
    - Implement token estimation for commits, log events, and metric data points
    - Implement truncation logic: preserve all commits, remove oldest logs first, then oldest metrics
    - Ensure resulting prompt fits within configured token limit
    - _Requirements: 4.5, 4.6_

  - [ ]* 8.2 Write property test for prompt construction completeness
    - **Property 6: Prompt Construction Completeness**
    - **Validates: Requirements 4.2**

  - [ ]* 8.3 Write property test for token-aware truncation ordering
    - **Property 7: Token-Aware Truncation Ordering**
    - **Validates: Requirements 4.5, 4.6**

  - [ ] 8.4 Implement Bedrock Claude integration
    - Implement prompt construction including full commit list, log events, metric data points, and time window boundaries
    - Implement Bedrock Runtime API call with 60-second timeout
    - Parse Bedrock response into `AnalysisOutput` structure (timeline entries, suspicious commits, root cause, rollback suggestions)
    - Map Bedrock errors to typed `AnalysisError` codes: BEDROCK_ERROR, AUTH_ERROR, TIMEOUT
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.7_

  - [ ]* 8.5 Write unit tests for AnalysisEngine
    - Test Bedrock error includes details
    - Test Bedrock auth error returns credential guidance
    - Test 60-second timeout behavior
    - Test prompt includes all data sources
    - _Requirements: 4.3, 4.4, 4.7, 4.2_

- [ ] 9. Implement Report Generation
  - [ ] 9.1 Implement ReportGenerator component
    - Create `src/components/report-generator.ts`
    - Implement timeline assembly: merge commits, log events, and metric data points chronologically; sort ascending by timestamp with tie-breaking (commits first, then logs, then metrics)
    - Implement root cause truncation to 500 characters
    - Implement rollback suggestion formatting with `git revert {sha}` commands
    - Handle empty suspicious commits with explanatory note
    - Produce Incident_Report within 5 seconds
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [ ]* 9.2 Write property test for timeline chronological ordering
    - **Property 8: Timeline Chronological Ordering**
    - **Validates: Requirements 5.2**

  - [ ]* 9.3 Write property test for root cause length constraint
    - **Property 9: Root Cause Length Constraint**
    - **Validates: Requirements 5.4**

  - [ ]* 9.4 Write property test for rollback command format
    - **Property 10: Rollback Command Format**
    - **Validates: Requirements 5.5**

  - [ ]* 9.5 Write unit tests for ReportGenerator
    - Test suspicious commits include confidence and explanation
    - Test report contains all labeled sections
    - Test no suspicious commits produces note
    - _Requirements: 5.3, 5.6, 5.7_

- [ ] 10. Implement Serialization and Parsing
  - [ ] 10.1 Implement report serialization and parsing
    - Create `src/components/report-serializer.ts`
    - Implement `serialize(report: IncidentReport): string` to produce JSON with all sections
    - Implement `parse(json: string): Result<IncidentReport, ParseError>` with schema validation
    - Return INVALID_JSON error for syntactically invalid JSON
    - Return SCHEMA_VIOLATION error with field-level details for schema violations
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 10.2 Write property test for serialization round-trip
    - **Property 11: Incident Report Serialization Round-Trip**
    - **Validates: Requirements 6.1, 6.2, 6.3**

  - [ ]* 10.3 Write property test for schema violation error reporting
    - **Property 12: Schema Violation Error Reporting**
    - **Validates: Requirements 6.4**

  - [ ]* 10.4 Write unit tests for serialization
    - Test invalid JSON returns INVALID_JSON error
    - Test valid round-trip for complex reports
    - _Requirements: 6.5, 6.3_

- [ ] 11. Checkpoint - Validate analysis and report layer
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Wire components together into CLI pipeline
  - [ ] 12.1 Implement pipeline orchestrator
    - Create `src/pipeline.ts`
    - Wire InputValidator → TimeWindowResolver → parallel(CommitFetcher, LogFetcher) → AnalysisEngine → ReportGenerator → Serializer
    - Implement parallel data fetching using `Promise.all` for CommitFetcher and LogFetcher
    - Propagate errors at each stage with proper Result type handling
    - _Requirements: 1.1, 1.2, 2.1, 3.1, 4.1, 5.1_

  - [ ] 12.2 Implement CLI entry point
    - Create `src/cli.ts`
    - Parse command-line arguments for repo URL, time range (start/end), alarm ARN, and log group/metric configuration
    - Call pipeline orchestrator and output result to stdout as JSON
    - Display human-readable errors to stderr
    - _Requirements: 1.1, 1.2, 1.6_

  - [ ]* 12.3 Write integration tests for full pipeline
    - Test full pipeline: valid input → fetch → analyze → report (with mocked external services)
    - Test pipeline with alarm resolution as time source
    - Test pipeline with empty commits (graceful degradation)
    - Test pipeline with data exceeding token limits
    - _Requirements: 1.1, 1.2, 2.5, 4.5_

- [ ] 13. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All external API calls (GitHub, CloudWatch, Bedrock) should be mocked in tests
- The retry utility is shared across CommitFetcher and LogFetcher

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2"] },
    { "id": 2, "tasks": ["2.1", "3.1", "5.2"] },
    { "id": 3, "tasks": ["2.2", "2.3", "2.4", "3.2", "5.1"] },
    { "id": 4, "tasks": ["5.3", "5.4", "5.5", "6.1"] },
    { "id": 5, "tasks": ["6.2", "6.3", "6.4", "6.5"] },
    { "id": 6, "tasks": ["8.1"] },
    { "id": 7, "tasks": ["8.2", "8.3", "8.4"] },
    { "id": 8, "tasks": ["8.5", "9.1"] },
    { "id": 9, "tasks": ["9.2", "9.3", "9.4", "9.5", "10.1"] },
    { "id": 10, "tasks": ["10.2", "10.3", "10.4"] },
    { "id": 11, "tasks": ["12.1"] },
    { "id": 12, "tasks": ["12.2", "12.3"] }
  ]
}
```
