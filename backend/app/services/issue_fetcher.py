"""Fetches GitHub issues within the investigation time window."""

from typing import List

from github import Auth, Github, GithubException

from app.config import settings
from app.models import ErrorResponse, IssueData, TimeWindow

MAX_ISSUES = 50


async def fetch_issues(
    owner: str, repo: str, time_window: TimeWindow, github_token: str | None = None
) -> List[IssueData] | ErrorResponse:
    """Fetch issues from GitHub created or updated within the given time window.

    No retries — fail fast on all errors.

    Args:
        owner: GitHub repository owner.
        repo: GitHub repository name.
        time_window: The investigation time window.
        github_token: Optional user-provided GitHub token.

    Returns:
        List of IssueData on success, or ErrorResponse on failure.
    """
    try:
        # Prefer user-provided token, fall back to .env config
        token = github_token or settings.GITHUB_TOKEN
        if token:
            auth = Auth.Token(token)
            g = Github(auth=auth, retry=None, per_page=100)
        else:
            g = Github(retry=None, per_page=100)

        repository = g.get_repo(f"{owner}/{repo}")
        issues = repository.get_issues(state="all", since=time_window.start)

        issue_list: List[IssueData] = []
        count = 0

        for issue in issues:
            if count >= MAX_ISSUES:
                break

            # Filter: only include issues updated within the time window
            updated = issue.updated_at
            if updated and updated > time_window.end:
                continue
            if updated and updated < time_window.start:
                continue

            # Truncate body to 500 chars
            body = issue.body or ""
            if len(body) > 500:
                body = body[:500] + "..."

            labels = [label.name for label in issue.labels]

            issue_data = IssueData(
                number=issue.number,
                title=issue.title or "",
                state=issue.state or "open",
                createdAt=issue.created_at.isoformat() if issue.created_at else "",
                updatedAt=issue.updated_at.isoformat() if issue.updated_at else "",
                labels=labels,
                body=body if body else None,
                url=issue.html_url or "",
            )
            issue_list.append(issue_data)
            count += 1

        g.close()
        return issue_list

    except GithubException as e:
        if e.status == 401:
            return ErrorResponse(
                code="AUTH_ERROR",
                message="Valid GitHub credentials are required. Set GITHUB_TOKEN in your .env file.",
            )
        elif e.status == 403:
            return ErrorResponse(
                code="RATE_LIMITED",
                message="GitHub API rate limit exceeded or access forbidden.",
            )
        elif e.status == 404:
            return ErrorResponse(
                code="NOT_FOUND",
                message=f"Repository {owner}/{repo} not found or not accessible.",
            )
        else:
            return ErrorResponse(
                code="GITHUB_ERROR",
                message=f"GitHub API error (HTTP {e.status}): {str(e.data)[:200]}",
            )
    except Exception as e:
        return ErrorResponse(
            code="API_UNAVAILABLE",
            message=f"Failed to fetch issues from GitHub API: {str(e)[:200]}",
        )
