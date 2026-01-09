"""
Git operations tools for agent workflows.

Provides git functionality for cloning, committing, pushing, and PR creation.
All operations are performed within isolated VM workspaces.
"""

import os
import subprocess
import tempfile
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import logging
import shutil

from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class GitCloneInput(BaseModel):
    """Input for cloning a repository."""

    repo_url: str = Field(description="HTTPS URL of the git repository")
    branch: Optional[str] = Field(default="main", description="Branch to clone")
    workspace_path: str = Field(description="Local path to clone repository to")
    depth: Optional[int] = Field(default=None, description="Shallow clone depth")


class GitCommitInput(BaseModel):
    """Input for committing changes."""

    workspace_path: str = Field(description="Repository workspace path")
    message: str = Field(description="Commit message")
    files: List[str] = Field(description="List of files to stage and commit")
    author_name: Optional[str] = Field(default=None, description="Commit author name")
    author_email: Optional[str] = Field(default=None, description="Commit author email")


class GitPushInput(BaseModel):
    """Input for pushing changes."""

    workspace_path: str = Field(description="Repository workspace path")
    branch: str = Field(description="Branch to push to")
    force: bool = Field(default=False, description="Force push")
    set_upstream: bool = Field(default=True, description="Set upstream branch")


class GitBranchInput(BaseModel):
    """Input for branch operations."""

    workspace_path: str = Field(description="Repository workspace path")
    branch_name: str = Field(description="Branch name to create/checkout")
    from_branch: Optional[str] = Field(default=None, description="Base branch to create from")


class GitDiffInput(BaseModel):
    """Input for getting diff."""

    workspace_path: str = Field(description="Repository workspace path")
    cached: bool = Field(default=False, description="Show staged changes")
    branch: Optional[str] = Field(default=None, description="Compare with branch")


class GitTools:
    """Git operations toolkit for agents."""

    def __init__(self, github_token: Optional[str] = None):
        """Initialize with optional GitHub token for private repos."""
        self.github_token = github_token

    def _run_git_command(
        self, cmd: List[str], cwd: str, capture_output: bool = True
    ) -> Tuple[int, str, str]:
        """Run a git command and return result."""
        env = os.environ.copy()
        if self.github_token:
            # Set up git credentials for HTTPS
            env["GIT_ASKPASS"] = "echo"
            env["GIT_USERNAME"] = "oauth2"
            env["GIT_PASSWORD"] = self.github_token

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=capture_output,
                text=True,
                env=env,
                timeout=300,  # 5 minute timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"Git command timed out: {' '.join(cmd)}")
            return -1, "", "Command timed out"
        except Exception as e:
            logger.error(f"Git command failed: {e}")
            return -1, "", str(e)

    @tool
    def clone_repository(self, input: GitCloneInput) -> Dict[str, Any]:
        """
        Clone a git repository to the specified workspace.

        Returns:
            Dictionary with status, workspace path, and commit SHA
        """
        # Ensure workspace exists
        workspace = Path(input.workspace_path)
        workspace.mkdir(parents=True, exist_ok=True)

        # Build clone command
        cmd = ["git", "clone"]
        if input.depth:
            cmd.extend(["--depth", str(input.depth)])
        if input.branch and input.branch != "main":
            cmd.extend(["--branch", input.branch])

        # Add authentication to URL if token provided
        repo_url = input.repo_url
        if self.github_token and "github.com" in repo_url:
            # Convert HTTPS URL to include token
            repo_url = repo_url.replace(
                "https://github.com",
                f"https://oauth2:{self.github_token}@github.com"
            )

        cmd.extend([repo_url, str(workspace)])

        # Execute clone
        returncode, stdout, stderr = self._run_git_command(cmd, str(workspace.parent))

        if returncode != 0:
            return {
                "success": False,
                "error": f"Clone failed: {stderr}",
                "workspace": None,
            }

        # Get initial commit SHA
        returncode, commit_sha, _ = self._run_git_command(
            ["git", "rev-parse", "HEAD"],
            str(workspace)
        )

        return {
            "success": True,
            "workspace": str(workspace),
            "branch": input.branch or "main",
            "commit_sha": commit_sha.strip() if commit_sha else None,
        }

    @tool
    def commit_changes(self, input: GitCommitInput) -> Dict[str, Any]:
        """
        Stage and commit specified files.

        Returns:
            Dictionary with commit SHA and status
        """
        workspace = Path(input.workspace_path)
        if not workspace.exists():
            return {"success": False, "error": "Workspace does not exist"}

        # Configure git user if provided
        if input.author_name:
            self._run_git_command(
                ["git", "config", "user.name", input.author_name],
                str(workspace)
            )
        if input.author_email:
            self._run_git_command(
                ["git", "config", "user.email", input.author_email],
                str(workspace)
            )

        # Stage files
        for file_path in input.files:
            returncode, _, stderr = self._run_git_command(
                ["git", "add", file_path],
                str(workspace)
            )
            if returncode != 0:
                logger.warning(f"Failed to stage {file_path}: {stderr}")

        # Check if there are staged changes
        returncode, stdout, _ = self._run_git_command(
            ["git", "diff", "--cached", "--name-only"],
            str(workspace)
        )

        if not stdout.strip():
            return {
                "success": False,
                "error": "No changes to commit",
            }

        # Commit changes
        returncode, stdout, stderr = self._run_git_command(
            ["git", "commit", "-m", input.message],
            str(workspace)
        )

        if returncode != 0:
            return {
                "success": False,
                "error": f"Commit failed: {stderr}",
            }

        # Get commit SHA
        returncode, commit_sha, _ = self._run_git_command(
            ["git", "rev-parse", "HEAD"],
            str(workspace)
        )

        return {
            "success": True,
            "commit_sha": commit_sha.strip() if commit_sha else None,
            "message": input.message,
            "files_committed": input.files,
        }

    @tool
    def push_changes(self, input: GitPushInput) -> Dict[str, Any]:
        """
        Push commits to remote repository.

        Returns:
            Dictionary with push status
        """
        workspace = Path(input.workspace_path)
        if not workspace.exists():
            return {"success": False, "error": "Workspace does not exist"}

        # Build push command
        cmd = ["git", "push"]
        if input.force:
            cmd.append("--force")
        if input.set_upstream:
            cmd.extend(["--set-upstream", "origin", input.branch])
        else:
            cmd.extend(["origin", input.branch])

        # Execute push
        returncode, stdout, stderr = self._run_git_command(cmd, str(workspace))

        if returncode != 0:
            return {
                "success": False,
                "error": f"Push failed: {stderr}",
            }

        return {
            "success": True,
            "branch": input.branch,
            "message": "Changes pushed successfully",
        }

    @tool
    def create_branch(self, input: GitBranchInput) -> Dict[str, Any]:
        """
        Create and checkout a new branch.

        Returns:
            Dictionary with branch creation status
        """
        workspace = Path(input.workspace_path)
        if not workspace.exists():
            return {"success": False, "error": "Workspace does not exist"}

        # Checkout base branch if specified
        if input.from_branch:
            returncode, _, stderr = self._run_git_command(
                ["git", "checkout", input.from_branch],
                str(workspace)
            )
            if returncode != 0:
                return {
                    "success": False,
                    "error": f"Failed to checkout base branch: {stderr}",
                }

        # Create and checkout new branch
        returncode, _, stderr = self._run_git_command(
            ["git", "checkout", "-b", input.branch_name],
            str(workspace)
        )

        if returncode != 0:
            # Try just checking out if branch exists
            returncode, _, stderr = self._run_git_command(
                ["git", "checkout", input.branch_name],
                str(workspace)
            )
            if returncode != 0:
                return {
                    "success": False,
                    "error": f"Failed to create/checkout branch: {stderr}",
                }

        return {
            "success": True,
            "branch": input.branch_name,
            "from_branch": input.from_branch,
        }

    @tool
    def get_diff(self, input: GitDiffInput) -> Dict[str, Any]:
        """
        Get git diff for review.

        Returns:
            Dictionary with diff content
        """
        workspace = Path(input.workspace_path)
        if not workspace.exists():
            return {"success": False, "error": "Workspace does not exist"}

        # Build diff command
        cmd = ["git", "diff"]
        if input.cached:
            cmd.append("--cached")
        if input.branch:
            cmd.append(f"{input.branch}...HEAD")

        # Get diff
        returncode, diff_content, stderr = self._run_git_command(
            cmd,
            str(workspace)
        )

        if returncode != 0:
            return {
                "success": False,
                "error": f"Failed to get diff: {stderr}",
            }

        # Also get list of changed files
        cmd_files = ["git", "diff", "--name-status"]
        if input.cached:
            cmd_files.append("--cached")
        if input.branch:
            cmd_files.append(f"{input.branch}...HEAD")

        _, files_changed, _ = self._run_git_command(cmd_files, str(workspace))

        return {
            "success": True,
            "diff": diff_content,
            "files_changed": files_changed.strip().split("\n") if files_changed else [],
            "has_changes": bool(diff_content.strip()),
        }

    @tool
    def create_pull_request(
        self,
        workspace_path: str,
        title: str,
        body: str,
        base_branch: str = "main",
        head_branch: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a GitHub pull request using gh CLI.

        Returns:
            Dictionary with PR URL and number
        """
        workspace = Path(workspace_path)
        if not workspace.exists():
            return {"success": False, "error": "Workspace does not exist"}

        # Get current branch if not specified
        if not head_branch:
            returncode, current_branch, _ = self._run_git_command(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                str(workspace)
            )
            if returncode != 0:
                return {"success": False, "error": "Failed to get current branch"}
            head_branch = current_branch.strip()

        # Create PR using gh CLI
        cmd = [
            "gh", "pr", "create",
            "--title", title,
            "--body", body,
            "--base", base_branch,
            "--head", head_branch
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=str(workspace),
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Failed to create PR: {result.stderr}",
                }

            # Parse PR URL from output
            pr_url = result.stdout.strip()

            return {
                "success": True,
                "pr_url": pr_url,
                "title": title,
                "base": base_branch,
                "head": head_branch,
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "PR creation timed out"}
        except FileNotFoundError:
            return {"success": False, "error": "gh CLI not installed"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Export tool functions
def get_git_tools(github_token: Optional[str] = None) -> List:
    """Get list of git tools for agent use."""
    tools = GitTools(github_token)
    return [
        tools.clone_repository,
        tools.commit_changes,
        tools.push_changes,
        tools.create_branch,
        tools.get_diff,
        tools.create_pull_request,
    ]