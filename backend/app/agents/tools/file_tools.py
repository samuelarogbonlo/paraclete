"""
File operation tools for agent workflows.

Provides file system operations within isolated VM workspaces.
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
import fnmatch
import mimetypes

from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ReadFileInput(BaseModel):
    """Input for reading a file."""

    file_path: str = Field(description="Path to the file to read")
    encoding: str = Field(default="utf-8", description="File encoding")
    lines: Optional[int] = Field(default=None, description="Number of lines to read")


class WriteFileInput(BaseModel):
    """Input for writing a file."""

    file_path: str = Field(description="Path to the file to write")
    content: str = Field(description="Content to write to the file")
    encoding: str = Field(default="utf-8", description="File encoding")
    create_dirs: bool = Field(default=True, description="Create parent directories if needed")


class DeleteFileInput(BaseModel):
    """Input for deleting a file or directory."""

    path: str = Field(description="Path to delete")
    recursive: bool = Field(default=False, description="Delete directories recursively")


class ListDirectoryInput(BaseModel):
    """Input for listing directory contents."""

    directory: str = Field(description="Directory path to list")
    pattern: Optional[str] = Field(default=None, description="Glob pattern to filter files")
    recursive: bool = Field(default=False, description="List recursively")
    include_hidden: bool = Field(default=False, description="Include hidden files")


class SearchFilesInput(BaseModel):
    """Input for searching files."""

    directory: str = Field(description="Directory to search in")
    pattern: str = Field(description="Search pattern (glob or regex)")
    content_pattern: Optional[str] = Field(default=None, description="Pattern to search in file contents")
    file_extensions: Optional[List[str]] = Field(default=None, description="File extensions to include")
    exclude_dirs: Optional[List[str]] = Field(default=None, description="Directories to exclude")
    max_results: int = Field(default=100, description="Maximum number of results")


class FileTools:
    """File operations toolkit for agents."""

    def __init__(self, workspace_root: Optional[str] = None):
        """Initialize with optional workspace root for sandboxing."""
        self.workspace_root = Path(workspace_root) if workspace_root else Path.cwd()

    def _resolve_path(self, path: str) -> Path:
        """Resolve path within workspace root."""
        resolved = Path(path)
        if not resolved.is_absolute():
            resolved = self.workspace_root / resolved

        # Ensure path is within workspace (security)
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError:
            raise ValueError(f"Path {path} is outside workspace root")

        return resolved

    @tool
    def read_file(self, input: ReadFileInput) -> Dict[str, Any]:
        """
        Read contents of a file.

        Returns:
            Dictionary with file content and metadata
        """
        try:
            file_path = self._resolve_path(input.file_path)

            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {input.file_path}",
                    "content": None,
                }

            if not file_path.is_file():
                return {
                    "success": False,
                    "error": f"Path is not a file: {input.file_path}",
                    "content": None,
                }

            # Read file content
            with open(file_path, "r", encoding=input.encoding) as f:
                if input.lines:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= input.lines:
                            break
                        lines.append(line)
                    content = "".join(lines)
                else:
                    content = f.read()

            # Get file metadata
            stat = file_path.stat()
            mime_type, _ = mimetypes.guess_type(str(file_path))

            return {
                "success": True,
                "content": content,
                "path": str(file_path),
                "size": stat.st_size,
                "mime_type": mime_type,
                "lines_read": input.lines or content.count("\n") + 1,
            }

        except UnicodeDecodeError:
            return {
                "success": False,
                "error": f"Failed to decode file with {input.encoding} encoding",
                "content": None,
            }
        except Exception as e:
            logger.error(f"Failed to read file: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": None,
            }

    @tool
    def write_file(self, input: WriteFileInput) -> Dict[str, Any]:
        """
        Write content to a file.

        Returns:
            Dictionary with write status
        """
        try:
            file_path = self._resolve_path(input.file_path)

            # Create parent directories if needed
            if input.create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            with open(file_path, "w", encoding=input.encoding) as f:
                f.write(input.content)

            # Get file info
            stat = file_path.stat()

            return {
                "success": True,
                "path": str(file_path),
                "size": stat.st_size,
                "lines_written": input.content.count("\n") + 1,
            }

        except Exception as e:
            logger.error(f"Failed to write file: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    @tool
    def delete_file(self, input: DeleteFileInput) -> Dict[str, Any]:
        """
        Delete a file or directory.

        Returns:
            Dictionary with deletion status
        """
        try:
            path = self._resolve_path(input.path)

            if not path.exists():
                return {
                    "success": False,
                    "error": f"Path not found: {input.path}",
                }

            if path.is_file():
                path.unlink()
                deleted_type = "file"
            elif path.is_dir():
                if input.recursive:
                    shutil.rmtree(path)
                else:
                    path.rmdir()  # Only works if directory is empty
                deleted_type = "directory"
            else:
                return {
                    "success": False,
                    "error": f"Unknown path type: {input.path}",
                }

            return {
                "success": True,
                "path": str(path),
                "type": deleted_type,
            }

        except OSError as e:
            if "Directory not empty" in str(e):
                return {
                    "success": False,
                    "error": "Directory not empty. Use recursive=True to delete non-empty directories",
                }
            return {
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"Failed to delete path: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    @tool
    def list_directory(self, input: ListDirectoryInput) -> Dict[str, Any]:
        """
        List contents of a directory.

        Returns:
            Dictionary with directory listing
        """
        try:
            directory = self._resolve_path(input.directory)

            if not directory.exists():
                return {
                    "success": False,
                    "error": f"Directory not found: {input.directory}",
                    "entries": [],
                }

            if not directory.is_dir():
                return {
                    "success": False,
                    "error": f"Path is not a directory: {input.directory}",
                    "entries": [],
                }

            entries = []

            if input.recursive:
                # Recursive listing
                pattern = input.pattern or "*"
                for path in directory.rglob(pattern):
                    if not input.include_hidden and path.name.startswith("."):
                        continue

                    relative_path = path.relative_to(directory)
                    entries.append({
                        "name": path.name,
                        "path": str(relative_path),
                        "type": "directory" if path.is_dir() else "file",
                        "size": path.stat().st_size if path.is_file() else None,
                    })
            else:
                # Non-recursive listing
                pattern = input.pattern or "*"
                for path in directory.glob(pattern):
                    if not input.include_hidden and path.name.startswith("."):
                        continue

                    entries.append({
                        "name": path.name,
                        "path": path.name,
                        "type": "directory" if path.is_dir() else "file",
                        "size": path.stat().st_size if path.is_file() else None,
                    })

            # Sort entries: directories first, then files
            entries.sort(key=lambda x: (x["type"] != "directory", x["name"].lower()))

            return {
                "success": True,
                "directory": str(directory),
                "entries": entries,
                "total": len(entries),
            }

        except Exception as e:
            logger.error(f"Failed to list directory: {e}")
            return {
                "success": False,
                "error": str(e),
                "entries": [],
            }

    @tool
    def search_files(self, input: SearchFilesInput) -> Dict[str, Any]:
        """
        Search for files by name and/or content.

        Returns:
            Dictionary with search results
        """
        try:
            directory = self._resolve_path(input.directory)

            if not directory.exists():
                return {
                    "success": False,
                    "error": f"Directory not found: {input.directory}",
                    "results": [],
                }

            results = []
            exclude_dirs = set(input.exclude_dirs or [])

            # Search for files
            for path in directory.rglob(input.pattern):
                if len(results) >= input.max_results:
                    break

                # Skip if in excluded directory
                if any(excluded in path.parts for excluded in exclude_dirs):
                    continue

                # Skip if not matching extension filter
                if input.file_extensions:
                    if not any(path.suffix == f".{ext}" for ext in input.file_extensions):
                        continue

                if path.is_file():
                    # Check content if pattern provided
                    matches_content = True
                    matching_lines = []

                    if input.content_pattern:
                        matches_content = False
                        try:
                            with open(path, "r", encoding="utf-8") as f:
                                for line_num, line in enumerate(f, 1):
                                    if input.content_pattern in line:
                                        matches_content = True
                                        matching_lines.append({
                                            "line_number": line_num,
                                            "content": line.strip(),
                                        })
                                        if len(matching_lines) >= 5:  # Limit context
                                            break
                        except (UnicodeDecodeError, PermissionError):
                            continue

                    if matches_content:
                        relative_path = path.relative_to(directory)
                        results.append({
                            "path": str(relative_path),
                            "name": path.name,
                            "size": path.stat().st_size,
                            "matching_lines": matching_lines if input.content_pattern else [],
                        })

            return {
                "success": True,
                "directory": str(directory),
                "pattern": input.pattern,
                "content_pattern": input.content_pattern,
                "results": results,
                "total": len(results),
                "truncated": len(results) == input.max_results,
            }

        except Exception as e:
            logger.error(f"Failed to search files: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": [],
            }


# Export tool functions
def get_file_tools(workspace_root: Optional[str] = None) -> List:
    """Get list of file tools for agent use."""
    tools = FileTools(workspace_root)
    return [
        tools.read_file,
        tools.write_file,
        tools.delete_file,
        tools.list_directory,
        tools.search_files,
    ]