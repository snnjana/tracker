"""Fetches commits from GitHub API within the investigation time window."""

from typing import List

from github import Auth, Github, GithubException

from app.config import settings
from app.models import CommitData, ErrorResponse, TimeWindow

MAX_COMMITS = 250
MAX_CHANGED_FILES = 3000
MAX_MESSAGE_LENGTH = 72000
MAX_PATCH_LENGTH = 2000  # Per file, truncate large diffs
MAX_TOTAL_PATCH_LENGTH = 8000  # Total patch per commit


async def fetch_commits(
    owner: str, repo: str, time_window: TimeWindow, github_token: str | None = None
) -> List[CommitData] | ErrorResponse:
    """Fetch commits from GitHub within the given time window.

    No retries — rate limit and auth errors are returned immediately.
    Only server errors (5xx) would warrant retries, but for simplicity
    we fail fast on all errors to avoid long backoff waits.

    Args:
        owner: GitHub repository owner.
        repo: GitHub repository name.
        time_window: The investigation time window.

    Returns:
        List of CommitData on success, or ErrorResponse on failure.
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
        commits = repository.get_commits(
            since=time_window.start,
            until=time_window.end,
        )

        commit_list: List[CommitData] = []
        count = 0

        for commit in commits:
            if count >= MAX_COMMITS:
                break

            # Get changed files and patch content
            changed_files = []
            patches = []
            try:
                files = commit.files or []
                total_patch_len = 0
                for f in files[:MAX_CHANGED_FILES]:
                    changed_files.append(f.filename)
                    # Collect patch/diff for each file (truncated)
                    if f.patch and total_patch_len < MAX_TOTAL_PATCH_LENGTH:
                        file_patch = f.patch
                        if len(file_patch) > MAX_PATCH_LENGTH:
                            file_patch = file_patch[:MAX_PATCH_LENGTH] + "\n... (truncated)"
                        patches.append(f"--- {f.filename} ---\n{file_patch}")
                        total_patch_len += len(file_patch)
            except Exception:
                pass

            combined_patch = "\n".join(patches) if patches else None

            # Truncate message if needed
            message = commit.commit.message or ""
            if len(message) > MAX_MESSAGE_LENGTH:
                message = message[:MAX_MESSAGE_LENGTH]

            commit_data = CommitData(
                sha=commit.sha,
                author=commit.commit.author.name or "Unknown",
                authorEmail=commit.commit.author.email or "",
                timestamp=(
                    commit.commit.author.date.isoformat()
                    if commit.commit.author.date
                    else ""
                ),
                message=message,
                changedFiles=changed_files,
                patch=combined_patch,
            )
            commit_list.append(commit_data)
            count += 1

        g.close()
        return commit_list

    except GithubException as e:
        if e.status == 401:
            return ErrorResponse(
                code="AUTH_ERROR",
                message="Valid GitHub credentials are required. Set GITHUB_TOKEN in your .env file.",
            )
        elif e.status == 403:
            # Rate limit or other forbidden — fail immediately, no retry
            reset_header = ""
            if hasattr(e, "headers") and e.headers:
                reset_header = e.headers.get("X-RateLimit-Reset", "")

            if "rate limit" in str(e.data).lower() or "rate limit" in str(e).lower():
                msg = "GitHub API rate limit exceeded."
                if reset_header:
                    msg += f" Resets at timestamp: {reset_header}."
                msg += " Set a GITHUB_TOKEN in your .env file to get 5,000 requests/hour instead of 60."
                return ErrorResponse(
                    code="RATE_LIMITED",
                    message=msg,
                )
            else:
                return ErrorResponse(
                    code="FORBIDDEN",
                    message=f"GitHub API returned 403 Forbidden for {owner}/{repo}. "
                    "This may be a private repo — set GITHUB_TOKEN in .env.",
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
            message=f"Failed to connect to GitHub API: {str(e)[:200]}",
        )
