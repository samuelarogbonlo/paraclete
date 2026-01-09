"""
Test suite for file operation tools.

Tests file read, write, delete, list, and search operations.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from app.agents.tools.file_tools import (
    FileTools,
    ReadFileInput,
    WriteFileInput,
    DeleteFileInput,
    ListDirectoryInput,
    SearchFilesInput,
    get_file_tools,
)


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for testing."""
    temp_dir = tempfile.mkdtemp()
    workspace = Path(temp_dir)

    # Create test directory structure
    (workspace / 'src').mkdir()
    (workspace / 'src' / 'main.py').write_text('def main():\n    print("Hello")\n')
    (workspace / 'src' / 'utils.py').write_text('def helper():\n    pass\n')
    (workspace / 'tests').mkdir()
    (workspace / 'tests' / 'test_main.py').write_text('def test_main():\n    assert True\n')
    (workspace / 'README.md').write_text('# Project\n')
    (workspace / '.hidden').write_text('hidden file')

    yield workspace
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def file_tools(temp_workspace):
    """Create FileTools instance with test workspace."""
    return FileTools(workspace_root=str(temp_workspace))


class TestFileTools:
    """Tests for FileTools class."""

    def test_file_tools_initialization(self, temp_workspace):
        """Test FileTools initialization."""
        # With workspace root
        tools = FileTools(workspace_root=str(temp_workspace))
        assert tools.workspace_root == temp_workspace

        # Without workspace root (uses cwd)
        tools_cwd = FileTools()
        assert tools_cwd.workspace_root == Path.cwd()

    def test_resolve_path_relative(self, file_tools, temp_workspace):
        """Test resolving relative paths."""
        # Act
        resolved = file_tools._resolve_path('src/main.py')

        # Assert
        assert resolved == temp_workspace / 'src' / 'main.py'

    def test_resolve_path_absolute(self, file_tools, temp_workspace):
        """Test resolving absolute paths."""
        # Act
        resolved = file_tools._resolve_path(str(temp_workspace / 'src' / 'main.py'))

        # Assert
        assert resolved == temp_workspace / 'src' / 'main.py'

    def test_resolve_path_outside_workspace_raises_error(self, file_tools):
        """Test that paths outside workspace are rejected."""
        # Act & Assert
        with pytest.raises(ValueError, match='outside workspace root'):
            file_tools._resolve_path('../../etc/passwd')


class TestReadFile:
    """Tests for read_file tool."""

    def test_read_file_success(self, file_tools):
        """Test successful file reading."""
        # Arrange
        read_input = ReadFileInput(
            file_path='src/main.py',
            encoding='utf-8',
        )

        # Act
        result = file_tools.read_file(read_input)

        # Assert
        assert result['success'] is True
        assert 'def main():' in result['content']
        assert result['size'] > 0
        assert result['mime_type'] == 'text/x-python'

    def test_read_file_not_found(self, file_tools):
        """Test reading non-existent file."""
        # Arrange
        read_input = ReadFileInput(file_path='nonexistent.txt')

        # Act
        result = file_tools.read_file(read_input)

        # Assert
        assert result['success'] is False
        assert 'File not found' in result['error']
        assert result['content'] is None

    def test_read_file_limited_lines(self, file_tools):
        """Test reading limited number of lines."""
        # Arrange
        read_input = ReadFileInput(
            file_path='src/main.py',
            lines=1,
        )

        # Act
        result = file_tools.read_file(read_input)

        # Assert
        assert result['success'] is True
        assert result['lines_read'] == 1

    def test_read_file_directory_error(self, file_tools):
        """Test reading a directory instead of file."""
        # Arrange
        read_input = ReadFileInput(file_path='src')

        # Act
        result = file_tools.read_file(read_input)

        # Assert
        assert result['success'] is False
        assert 'not a file' in result['error']

    def test_read_file_encoding_error(self, file_tools, temp_workspace):
        """Test reading file with wrong encoding."""
        # Arrange - Create binary file
        binary_file = temp_workspace / 'binary.dat'
        binary_file.write_bytes(b'\x80\x81\x82')

        read_input = ReadFileInput(
            file_path='binary.dat',
            encoding='utf-8',
        )

        # Act
        result = file_tools.read_file(read_input)

        # Assert
        assert result['success'] is False
        assert 'decode' in result['error']


class TestWriteFile:
    """Tests for write_file tool."""

    def test_write_file_success(self, file_tools):
        """Test successful file writing."""
        # Arrange
        write_input = WriteFileInput(
            file_path='new_file.txt',
            content='New file content\n',
            encoding='utf-8',
        )

        # Act
        result = file_tools.write_file(write_input)

        # Assert
        assert result['success'] is True
        assert result['size'] > 0
        assert result['lines_written'] == 2  # Content + implicit newline

    def test_write_file_creates_directories(self, file_tools, temp_workspace):
        """Test writing file with directory creation."""
        # Arrange
        write_input = WriteFileInput(
            file_path='new_dir/subdir/file.txt',
            content='Content',
            create_dirs=True,
        )

        # Act
        result = file_tools.write_file(write_input)

        # Assert
        assert result['success'] is True
        assert (temp_workspace / 'new_dir' / 'subdir' / 'file.txt').exists()

    def test_write_file_overwrites_existing(self, file_tools, temp_workspace):
        """Test overwriting existing file."""
        # Arrange
        write_input = WriteFileInput(
            file_path='README.md',
            content='# New Content\n',
        )

        # Act
        result = file_tools.write_file(write_input)

        # Assert
        assert result['success'] is True
        assert (temp_workspace / 'README.md').read_text() == '# New Content\n'

    def test_write_file_without_create_dirs(self, file_tools):
        """Test writing to non-existent directory without create_dirs."""
        # Arrange
        write_input = WriteFileInput(
            file_path='nonexistent/file.txt',
            content='Content',
            create_dirs=False,
        )

        # Act
        result = file_tools.write_file(write_input)

        # Assert
        assert result['success'] is False


class TestDeleteFile:
    """Tests for delete_file tool."""

    def test_delete_file_success(self, file_tools, temp_workspace):
        """Test successful file deletion."""
        # Arrange
        delete_input = DeleteFileInput(
            path='README.md',
            recursive=False,
        )

        # Act
        result = file_tools.delete_file(delete_input)

        # Assert
        assert result['success'] is True
        assert result['type'] == 'file'
        assert not (temp_workspace / 'README.md').exists()

    def test_delete_directory_empty(self, file_tools, temp_workspace):
        """Test deleting empty directory."""
        # Arrange
        empty_dir = temp_workspace / 'empty'
        empty_dir.mkdir()

        delete_input = DeleteFileInput(
            path='empty',
            recursive=False,
        )

        # Act
        result = file_tools.delete_file(delete_input)

        # Assert
        assert result['success'] is True
        assert result['type'] == 'directory'

    def test_delete_directory_recursive(self, file_tools, temp_workspace):
        """Test deleting directory recursively."""
        # Arrange
        delete_input = DeleteFileInput(
            path='src',
            recursive=True,
        )

        # Act
        result = file_tools.delete_file(delete_input)

        # Assert
        assert result['success'] is True
        assert not (temp_workspace / 'src').exists()

    def test_delete_directory_not_empty_without_recursive(self, file_tools):
        """Test deleting non-empty directory without recursive."""
        # Arrange
        delete_input = DeleteFileInput(
            path='src',
            recursive=False,
        )

        # Act
        result = file_tools.delete_file(delete_input)

        # Assert
        assert result['success'] is False
        assert 'not empty' in result['error']

    def test_delete_nonexistent_path(self, file_tools):
        """Test deleting non-existent path."""
        # Arrange
        delete_input = DeleteFileInput(path='nonexistent.txt')

        # Act
        result = file_tools.delete_file(delete_input)

        # Assert
        assert result['success'] is False
        assert 'not found' in result['error']


class TestListDirectory:
    """Tests for list_directory tool."""

    def test_list_directory_success(self, file_tools):
        """Test successful directory listing."""
        # Arrange
        list_input = ListDirectoryInput(
            directory='src',
            include_hidden=False,
        )

        # Act
        result = file_tools.list_directory(list_input)

        # Assert
        assert result['success'] is True
        assert result['total'] == 2  # main.py, utils.py
        assert any(e['name'] == 'main.py' for e in result['entries'])
        assert any(e['name'] == 'utils.py' for e in result['entries'])

    def test_list_directory_with_pattern(self, file_tools):
        """Test listing with glob pattern."""
        # Arrange
        list_input = ListDirectoryInput(
            directory='src',
            pattern='*.py',
        )

        # Act
        result = file_tools.list_directory(list_input)

        # Assert
        assert result['success'] is True
        assert all(e['name'].endswith('.py') for e in result['entries'])

    def test_list_directory_recursive(self, file_tools):
        """Test recursive directory listing."""
        # Arrange
        list_input = ListDirectoryInput(
            directory='.',
            pattern='*.py',
            recursive=True,
        )

        # Act
        result = file_tools.list_directory(list_input)

        # Assert
        assert result['success'] is True
        assert result['total'] >= 3  # main.py, utils.py, test_main.py

    def test_list_directory_includes_hidden_with_flag(self, file_tools):
        """Test listing with hidden files."""
        # Arrange
        list_input = ListDirectoryInput(
            directory='.',
            include_hidden=True,
            recursive=False,
        )

        # Act
        result = file_tools.list_directory(list_input)

        # Assert
        assert result['success'] is True
        assert any(e['name'] == '.hidden' for e in result['entries'])

    def test_list_directory_excludes_hidden_by_default(self, file_tools):
        """Test that hidden files are excluded by default."""
        # Arrange
        list_input = ListDirectoryInput(
            directory='.',
            include_hidden=False,
        )

        # Act
        result = file_tools.list_directory(list_input)

        # Assert
        assert result['success'] is True
        assert not any(e['name'] == '.hidden' for e in result['entries'])

    def test_list_directory_sorts_directories_first(self, file_tools):
        """Test that directories are sorted before files."""
        # Arrange
        list_input = ListDirectoryInput(directory='.')

        # Act
        result = file_tools.list_directory(list_input)

        # Assert
        assert result['success'] is True

        # Check that directories come before files
        dir_indices = [i for i, e in enumerate(result['entries']) if e['type'] == 'directory']
        file_indices = [i for i, e in enumerate(result['entries']) if e['type'] == 'file']

        if dir_indices and file_indices:
            assert max(dir_indices) < min(file_indices)

    def test_list_directory_not_found(self, file_tools):
        """Test listing non-existent directory."""
        # Arrange
        list_input = ListDirectoryInput(directory='nonexistent')

        # Act
        result = file_tools.list_directory(list_input)

        # Assert
        assert result['success'] is False
        assert 'not found' in result['error']

    def test_list_directory_not_a_directory(self, file_tools):
        """Test listing a file instead of directory."""
        # Arrange
        list_input = ListDirectoryInput(directory='README.md')

        # Act
        result = file_tools.list_directory(list_input)

        # Assert
        assert result['success'] is False
        assert 'not a directory' in result['error']


class TestSearchFiles:
    """Tests for search_files tool."""

    def test_search_files_by_name(self, file_tools):
        """Test searching files by name pattern."""
        # Arrange
        search_input = SearchFilesInput(
            directory='.',
            pattern='*.py',
        )

        # Act
        result = file_tools.search_files(search_input)

        # Assert
        assert result['success'] is True
        assert result['total'] >= 3
        assert all(r['name'].endswith('.py') for r in result['results'])

    def test_search_files_by_content(self, file_tools):
        """Test searching files by content."""
        # Arrange
        search_input = SearchFilesInput(
            directory='.',
            pattern='*.py',
            content_pattern='def main',
        )

        # Act
        result = file_tools.search_files(search_input)

        # Assert
        assert result['success'] is True
        assert any('main.py' in r['path'] for r in result['results'])

        # Check that matching lines are included
        main_result = next(r for r in result['results'] if 'main.py' in r['path'])
        assert len(main_result['matching_lines']) > 0

    def test_search_files_with_extension_filter(self, file_tools):
        """Test searching with file extension filter."""
        # Arrange
        search_input = SearchFilesInput(
            directory='.',
            pattern='*',
            file_extensions=['py'],
        )

        # Act
        result = file_tools.search_files(search_input)

        # Assert
        assert result['success'] is True
        assert all(r['name'].endswith('.py') for r in result['results'])

    def test_search_files_with_exclude_dirs(self, file_tools):
        """Test searching with excluded directories."""
        # Arrange
        search_input = SearchFilesInput(
            directory='.',
            pattern='*.py',
            exclude_dirs=['tests'],
        )

        # Act
        result = file_tools.search_files(search_input)

        # Assert
        assert result['success'] is True
        assert not any('tests' in r['path'] for r in result['results'])

    def test_search_files_max_results(self, file_tools):
        """Test search with max results limit."""
        # Arrange
        search_input = SearchFilesInput(
            directory='.',
            pattern='*',
            max_results=2,
        )

        # Act
        result = file_tools.search_files(search_input)

        # Assert
        assert result['success'] is True
        assert len(result['results']) <= 2
        assert result['truncated'] is True

    def test_search_files_content_limits_matching_lines(self, file_tools, temp_workspace):
        """Test that matching lines are limited."""
        # Arrange - Create file with many matching lines
        many_lines = temp_workspace / 'many.py'
        many_lines.write_text('def func():\n' * 10)

        search_input = SearchFilesInput(
            directory='.',
            pattern='many.py',
            content_pattern='def func',
        )

        # Act
        result = file_tools.search_files(search_input)

        # Assert
        assert result['success'] is True
        matching_result = result['results'][0]
        assert len(matching_result['matching_lines']) == 5  # Limited to 5


class TestGetFileTools:
    """Tests for get_file_tools helper function."""

    def test_get_file_tools_returns_list(self):
        """Test that get_file_tools returns list of tools."""
        # Act
        tools = get_file_tools()

        # Assert
        assert isinstance(tools, list)
        assert len(tools) == 5  # 5 tools

    def test_get_file_tools_with_workspace(self, temp_workspace):
        """Test get_file_tools with workspace root."""
        # Act
        tools = get_file_tools(workspace_root=str(temp_workspace))

        # Assert
        assert isinstance(tools, list)
        assert len(tools) == 5

    def test_get_file_tools_contains_all_tools(self):
        """Test that all file tools are included."""
        # Act
        tools = get_file_tools()
        tool_names = [tool.name for tool in tools]

        # Assert
        assert 'read_file' in tool_names
        assert 'write_file' in tool_names
        assert 'delete_file' in tool_names
        assert 'list_directory' in tool_names
        assert 'search_files' in tool_names
