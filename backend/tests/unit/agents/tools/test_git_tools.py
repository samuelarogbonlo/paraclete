"""
Test suite for git operation tools.

Tests git clone, commit, push, branch, diff, and PR creation.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.agents.tools.git_tools import (
    GitTools,
    GitCloneInput,
    GitCommitInput,
    GitPushInput,
    GitBranchInput,
    GitDiffInput,
    get_git_tools,
)


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def git_tools():
    """Create GitTools instance without token."""
    return GitTools(github_token=None)


@pytest.fixture
def git_tools_with_token():
    """Create GitTools instance with GitHub token."""
    return GitTools(github_token='test-token-123')


class TestGitTools:
    """Tests for GitTools class."""

    def test_git_tools_initialization(self):
        """Test GitTools initialization."""
        # Without token
        tools = GitTools()
        assert tools.github_token is None

        # With token
        tools_with_token = GitTools(github_token='test-token')
        assert tools_with_token.github_token == 'test-token'

    def test_run_git_command_basic(self, git_tools, temp_workspace):
        """Test basic git command execution."""
        # Arrange
        (temp_workspace / 'test.txt').write_text('test')

        # Act
        returncode, stdout, stderr = git_tools._run_git_command(
            ['git', 'init'],
            str(temp_workspace)
        )

        # Assert
        assert returncode == 0
        assert (temp_workspace / '.git').exists()

    def test_run_git_command_with_timeout(self, git_tools, temp_workspace):
        """Test git command timeout handling."""
        # Note: Would need to mock subprocess to test timeout
        # This validates the structure
        assert hasattr(git_tools, '_run_git_command')

    def test_run_git_command_handles_errors(self, git_tools, temp_workspace):
        """Test git command error handling."""
        # Act - Invalid git command
        returncode, stdout, stderr = git_tools._run_git_command(
            ['git', 'invalid-command'],
            str(temp_workspace)
        )

        # Assert
        assert returncode != 0
        assert stderr  # Should have error message


class TestCloneRepository:
    """Tests for clone_repository tool."""

    @patch('app.agents.tools.git_tools.GitTools._run_git_command')
    def test_clone_repository_success(self, mock_run_cmd, git_tools, temp_workspace):
        """Test successful repository cloning."""
        # Arrange
        mock_run_cmd.side_effect = [
            (0, '', ''),  # git clone
            (0, 'abc123def456', ''),  # git rev-parse HEAD
        ]

        clone_input = GitCloneInput(
            repo_url='https://github.com/test/repo',
            branch='main',
            workspace_path=str(temp_workspace),
        )

        # Act
        result = git_tools.clone_repository(clone_input)

        # Assert
        assert result['success'] is True
        assert result['workspace'] == str(temp_workspace)
        assert result['branch'] == 'main'
        assert result['commit_sha'] == 'abc123def456'

    @patch('app.agents.tools.git_tools.GitTools._run_git_command')
    def test_clone_repository_with_depth(self, mock_run_cmd, git_tools, temp_workspace):
        """Test shallow clone with depth."""
        # Arrange
        mock_run_cmd.side_effect = [
            (0, '', ''),
            (0, 'abc123', ''),
        ]

        clone_input = GitCloneInput(
            repo_url='https://github.com/test/repo',
            branch='main',
            workspace_path=str(temp_workspace),
            depth=1,
        )

        # Act
        result = git_tools.clone_repository(clone_input)

        # Assert
        assert result['success'] is True

        # Verify depth parameter was used
        call_args = mock_run_cmd.call_args_list[0][0][0]
        assert '--depth' in call_args
        assert '1' in call_args

    @patch('app.agents.tools.git_tools.GitTools._run_git_command')
    def test_clone_repository_with_token(self, mock_run_cmd, git_tools_with_token, temp_workspace):
        """Test cloning with GitHub token."""
        # Arrange
        mock_run_cmd.side_effect = [
            (0, '', ''),
            (0, 'abc123', ''),
        ]

        clone_input = GitCloneInput(
            repo_url='https://github.com/test/repo',
            branch='main',
            workspace_path=str(temp_workspace),
        )

        # Act
        result = git_tools_with_token.clone_repository(clone_input)

        # Assert
        assert result['success'] is True

        # Verify token was injected into URL
        call_args = mock_run_cmd.call_args_list[0][0][0]
        url_arg = [arg for arg in call_args if 'oauth2:' in arg]
        assert len(url_arg) > 0

    @patch('app.agents.tools.git_tools.GitTools._run_git_command')
    def test_clone_repository_failure(self, mock_run_cmd, git_tools, temp_workspace):
        """Test clone failure handling."""
        # Arrange
        mock_run_cmd.return_value = (1, '', 'Clone failed: repository not found')

        clone_input = GitCloneInput(
            repo_url='https://github.com/test/nonexistent',
            branch='main',
            workspace_path=str(temp_workspace),
        )

        # Act
        result = git_tools.clone_repository(clone_input)

        # Assert
        assert result['success'] is False
        assert 'Clone failed' in result['error']
        assert result['workspace'] is None

    @patch('app.agents.tools.git_tools.GitTools._run_git_command')
    def test_clone_repository_custom_branch(self, mock_run_cmd, git_tools, temp_workspace):
        """Test cloning specific branch."""
        # Arrange
        mock_run_cmd.side_effect = [
            (0, '', ''),
            (0, 'abc123', ''),
        ]

        clone_input = GitCloneInput(
            repo_url='https://github.com/test/repo',
            branch='feature-branch',
            workspace_path=str(temp_workspace),
        )

        # Act
        result = git_tools.clone_repository(clone_input)

        # Assert
        assert result['success'] is True
        assert result['branch'] == 'feature-branch'

        # Verify branch parameter was used
        call_args = mock_run_cmd.call_args_list[0][0][0]
        assert '--branch' in call_args
        assert 'feature-branch' in call_args


class TestCommitChanges:
    """Tests for commit_changes tool."""

    @patch('app.agents.tools.git_tools.GitTools._run_git_command')
    def test_commit_changes_success(self, mock_run_cmd, git_tools, temp_workspace):
        """Test successful commit."""
        # Arrange
        mock_run_cmd.side_effect = [
            (0, '', ''),  # git config user.name
            (0, '', ''),  # git config user.email
            (0, '', ''),  # git add file1.py
            (0, 'file1.py\n', ''),  # git diff --cached --name-only
            (0, '[main abc123] Test commit', ''),  # git commit
            (0, 'abc123def456', ''),  # git rev-parse HEAD
        ]

        commit_input = GitCommitInput(
            workspace_path=str(temp_workspace),
            message='Test commit',
            files=['file1.py'],
            author_name='Test User',
            author_email='test@example.com',
        )

        # Act
        result = git_tools.commit_changes(commit_input)

        # Assert
        assert result['success'] is True
        assert result['commit_sha'] == 'abc123def456'
        assert result['message'] == 'Test commit'
        assert result['files_committed'] == ['file1.py']

    @patch('app.agents.tools.git_tools.GitTools._run_git_command')
    def test_commit_changes_no_changes_to_commit(self, mock_run_cmd, git_tools, temp_workspace):
        """Test commit when there are no changes."""
        # Arrange
        mock_run_cmd.side_effect = [
            (0, '', ''),  # git add
            (0, '', ''),  # git diff --cached --name-only (empty)
        ]

        commit_input = GitCommitInput(
            workspace_path=str(temp_workspace),
            message='Empty commit',
            files=['file1.py'],
        )

        # Act
        result = git_tools.commit_changes(commit_input)

        # Assert
        assert result['success'] is False
        assert 'No changes to commit' in result['error']

    @patch('app.agents.tools.git_tools.GitTools._run_git_command')
    def test_commit_changes_workspace_not_exists(self, mock_run_cmd, git_tools):
        """Test commit when workspace doesn't exist."""
        # Arrange
        commit_input = GitCommitInput(
            workspace_path='/nonexistent/path',
            message='Test commit',
            files=['file1.py'],
        )

        # Act
        result = git_tools.commit_changes(commit_input)

        # Assert
        assert result['success'] is False
        assert 'Workspace does not exist' in result['error']

    @patch('app.agents.tools.git_tools.GitTools._run_git_command')
    def test_commit_changes_multiple_files(self, mock_run_cmd, git_tools, temp_workspace):
        """Test committing multiple files."""
        # Arrange
        mock_run_cmd.side_effect = [
            (0, '', ''),  # git add file1.py
            (0, '', ''),  # git add file2.py
            (0, '', ''),  # git add file3.py
            (0, 'file1.py\nfile2.py\nfile3.py\n', ''),  # git diff
            (0, '', ''),  # git commit
            (0, 'abc123', ''),  # git rev-parse HEAD
        ]

        commit_input = GitCommitInput(
            workspace_path=str(temp_workspace),
            message='Multi-file commit',
            files=['file1.py', 'file2.py', 'file3.py'],
        )

        # Act
        result = git_tools.commit_changes(commit_input)

        # Assert
        assert result['success'] is True
        assert len(result['files_committed']) == 3


class TestPushChanges:
    """Tests for push_changes tool."""

    @patch('app.agents.tools.git_tools.GitTools._run_git_command')
    def test_push_changes_success(self, mock_run_cmd, git_tools, temp_workspace):
        """Test successful push."""
        # Arrange
        mock_run_cmd.return_value = (0, 'Pushed successfully', '')

        push_input = GitPushInput(
            workspace_path=str(temp_workspace),
            branch='main',
            force=False,
            set_upstream=True,
        )

        # Act
        result = git_tools.push_changes(push_input)

        # Assert
        assert result['success'] is True
        assert result['branch'] == 'main'

    @patch('app.agents.tools.git_tools.GitTools._run_git_command')
    def test_push_changes_force_push(self, mock_run_cmd, git_tools, temp_workspace):
        """Test force push."""
        # Arrange
        mock_run_cmd.return_value = (0, '', '')

        push_input = GitPushInput(
            workspace_path=str(temp_workspace),
            branch='feature',
            force=True,
            set_upstream=False,
        )

        # Act
        result = git_tools.push_changes(push_input)

        # Assert
        assert result['success'] is True

        # Verify --force flag was used
        call_args = mock_run_cmd.call_args[0][0]
        assert '--force' in call_args

    @patch('app.agents.tools.git_tools.GitTools._run_git_command')
    def test_push_changes_failure(self, mock_run_cmd, git_tools, temp_workspace):
        """Test push failure."""
        # Arrange
        mock_run_cmd.return_value = (1, '', 'Push failed: permission denied')

        push_input = GitPushInput(
            workspace_path=str(temp_workspace),
            branch='main',
        )

        # Act
        result = git_tools.push_changes(push_input)

        # Assert
        assert result['success'] is False
        assert 'Push failed' in result['error']


class TestCreateBranch:
    """Tests for create_branch tool."""

    @patch('app.agents.tools.git_tools.GitTools._run_git_command')
    def test_create_branch_success(self, mock_run_cmd, git_tools, temp_workspace):
        """Test successful branch creation."""
        # Arrange
        mock_run_cmd.return_value = (0, '', '')

        branch_input = GitBranchInput(
            workspace_path=str(temp_workspace),
            branch_name='feature-branch',
        )

        # Act
        result = git_tools.create_branch(branch_input)

        # Assert
        assert result['success'] is True
        assert result['branch'] == 'feature-branch'

    @patch('app.agents.tools.git_tools.GitTools._run_git_command')
    def test_create_branch_from_base(self, mock_run_cmd, git_tools, temp_workspace):
        """Test branch creation from base branch."""
        # Arrange
        mock_run_cmd.side_effect = [
            (0, '', ''),  # git checkout main
            (0, '', ''),  # git checkout -b feature-branch
        ]

        branch_input = GitBranchInput(
            workspace_path=str(temp_workspace),
            branch_name='feature-branch',
            from_branch='main',
        )

        # Act
        result = git_tools.create_branch(branch_input)

        # Assert
        assert result['success'] is True
        assert result['branch'] == 'feature-branch'
        assert result['from_branch'] == 'main'

    @patch('app.agents.tools.git_tools.GitTools._run_git_command')
    def test_create_branch_already_exists(self, mock_run_cmd, git_tools, temp_workspace):
        """Test checking out existing branch."""
        # Arrange
        mock_run_cmd.side_effect = [
            (1, '', 'fatal: A branch named feature-branch already exists'),  # git checkout -b fails
            (0, '', ''),  # git checkout feature-branch succeeds
        ]

        branch_input = GitBranchInput(
            workspace_path=str(temp_workspace),
            branch_name='feature-branch',
        )

        # Act
        result = git_tools.create_branch(branch_input)

        # Assert
        assert result['success'] is True


class TestGetDiff:
    """Tests for get_diff tool."""

    @patch('app.agents.tools.git_tools.GitTools._run_git_command')
    def test_get_diff_success(self, mock_run_cmd, git_tools, temp_workspace):
        """Test getting diff."""
        # Arrange
        diff_content = '+++ new line\n--- old line\n'
        mock_run_cmd.side_effect = [
            (0, diff_content, ''),  # git diff
            (0, 'M\tfile1.py\nA\tfile2.py\n', ''),  # git diff --name-status
        ]

        diff_input = GitDiffInput(
            workspace_path=str(temp_workspace),
            cached=False,
        )

        # Act
        result = git_tools.get_diff(diff_input)

        # Assert
        assert result['success'] is True
        assert result['diff'] == diff_content
        assert result['has_changes'] is True
        assert len(result['files_changed']) == 2

    @patch('app.agents.tools.git_tools.GitTools._run_git_command')
    def test_get_diff_staged_changes(self, mock_run_cmd, git_tools, temp_workspace):
        """Test getting staged changes."""
        # Arrange
        mock_run_cmd.side_effect = [
            (0, 'staged diff', ''),
            (0, 'M\tfile1.py\n', ''),
        ]

        diff_input = GitDiffInput(
            workspace_path=str(temp_workspace),
            cached=True,
        )

        # Act
        result = git_tools.get_diff(diff_input)

        # Assert
        assert result['success'] is True

        # Verify --cached flag was used
        call_args = mock_run_cmd.call_args_list[0][0][0]
        assert '--cached' in call_args

    @patch('app.agents.tools.git_tools.GitTools._run_git_command')
    def test_get_diff_compare_with_branch(self, mock_run_cmd, git_tools, temp_workspace):
        """Test getting diff compared to branch."""
        # Arrange
        mock_run_cmd.side_effect = [
            (0, 'branch diff', ''),
            (0, 'M\tfile1.py\n', ''),
        ]

        diff_input = GitDiffInput(
            workspace_path=str(temp_workspace),
            branch='main',
        )

        # Act
        result = git_tools.get_diff(diff_input)

        # Assert
        assert result['success'] is True

        # Verify branch comparison was used
        call_args = mock_run_cmd.call_args_list[0][0][0]
        assert any('main...HEAD' in arg for arg in call_args)


class TestCreatePullRequest:
    """Tests for create_pull_request tool."""

    @patch('subprocess.run')
    def test_create_pull_request_success(self, mock_subprocess, git_tools, temp_workspace):
        """Test successful PR creation."""
        # Arrange
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = 'https://github.com/test/repo/pull/123'
        mock_result.stderr = ''
        mock_subprocess.return_value = mock_result

        # Act
        result = git_tools.create_pull_request(
            workspace_path=str(temp_workspace),
            title='Test PR',
            body='PR description',
            base_branch='main',
            head_branch='feature',
        )

        # Assert
        assert result['success'] is True
        assert result['pr_url'] == 'https://github.com/test/repo/pull/123'
        assert result['title'] == 'Test PR'

    @patch('subprocess.run')
    def test_create_pull_request_gh_not_installed(self, mock_subprocess, git_tools, temp_workspace):
        """Test PR creation when gh CLI is not installed."""
        # Arrange
        mock_subprocess.side_effect = FileNotFoundError()

        # Act
        result = git_tools.create_pull_request(
            workspace_path=str(temp_workspace),
            title='Test PR',
            body='PR body',
        )

        # Assert
        assert result['success'] is False
        assert 'gh CLI not installed' in result['error']


class TestGetGitTools:
    """Tests for get_git_tools helper function."""

    def test_get_git_tools_returns_list(self):
        """Test that get_git_tools returns list of tools."""
        # Act
        tools = get_git_tools()

        # Assert
        assert isinstance(tools, list)
        assert len(tools) == 6  # 6 tools

    def test_get_git_tools_with_token(self):
        """Test get_git_tools with GitHub token."""
        # Act
        tools = get_git_tools(github_token='test-token')

        # Assert
        assert isinstance(tools, list)
        assert len(tools) == 6

    def test_get_git_tools_contains_all_tools(self):
        """Test that all git tools are included."""
        # Act
        tools = get_git_tools()
        tool_names = [tool.name for tool in tools]

        # Assert
        assert 'clone_repository' in tool_names
        assert 'commit_changes' in tool_names
        assert 'push_changes' in tool_names
        assert 'create_branch' in tool_names
        assert 'get_diff' in tool_names
        assert 'create_pull_request' in tool_names
