"""
Search and research tools for agent workflows.

Provides web search and documentation lookup capabilities.
"""

import os
import json
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import aiohttp

from langchain_core.tools import tool
from langchain_community.utilities import GoogleSearchAPIWrapper, DuckDuckGoSearchAPIWrapper
from langchain_community.document_loaders import WebBaseLoader
from pydantic import BaseModel, Field
import requests

logger = logging.getLogger(__name__)


class WebSearchInput(BaseModel):
    """Input for web search."""

    query: str = Field(description="Search query")
    num_results: int = Field(default=5, description="Number of results to return")
    search_type: str = Field(default="general", description="Type of search: general, news, academic")
    recency_days: Optional[int] = Field(default=None, description="Filter to results from last N days")


class DocumentationSearchInput(BaseModel):
    """Input for documentation search."""

    query: str = Field(description="Search query")
    source: str = Field(description="Documentation source: langchain, openai, anthropic, github, python, etc.")
    version: Optional[str] = Field(default=None, description="Specific version to search")
    num_results: int = Field(default=5, description="Number of results to return")


class WebPageSummaryInput(BaseModel):
    """Input for summarizing a web page."""

    url: str = Field(description="URL to summarize")
    max_length: int = Field(default=500, description="Maximum summary length in words")
    focus_areas: Optional[List[str]] = Field(default=None, description="Specific areas to focus on")


class GitHubSearchInput(BaseModel):
    """Input for GitHub search."""

    query: str = Field(description="Search query")
    search_type: str = Field(default="repositories", description="Type: repositories, code, issues, users")
    language: Optional[str] = Field(default=None, description="Programming language filter")
    sort: str = Field(default="stars", description="Sort by: stars, forks, updated")
    num_results: int = Field(default=10, description="Number of results")


class SearchTools:
    """Search and research toolkit for agents."""

    def __init__(
        self,
        google_api_key: Optional[str] = None,
        google_cse_id: Optional[str] = None,
        github_token: Optional[str] = None,
        use_fallback: bool = True,
    ):
        """Initialize search tools with API keys."""
        self.google_api_key = google_api_key or os.getenv("GOOGLE_API_KEY")
        self.google_cse_id = google_cse_id or os.getenv("GOOGLE_CSE_ID")
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.use_fallback = use_fallback

        # Initialize search wrappers
        self._init_search_wrappers()

    def _init_search_wrappers(self):
        """Initialize search API wrappers."""
        if self.google_api_key and self.google_cse_id:
            try:
                self.google_search = GoogleSearchAPIWrapper(
                    google_api_key=self.google_api_key,
                    google_cse_id=self.google_cse_id,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Google Search: {e}")
                self.google_search = None
        else:
            self.google_search = None

        # DuckDuckGo as fallback (no API key needed)
        if self.use_fallback:
            try:
                self.ddg_search = DuckDuckGoSearchAPIWrapper()
            except Exception as e:
                logger.warning(f"Failed to initialize DuckDuckGo Search: {e}")
                self.ddg_search = None
        else:
            self.ddg_search = None

    @tool
    def web_search(self, input: WebSearchInput) -> Dict[str, Any]:
        """
        Perform web search using available search engines.

        Returns:
            Dictionary with search results
        """
        try:
            # Build query with filters
            query = input.query
            if input.recency_days:
                date_filter = (datetime.now() - timedelta(days=input.recency_days)).strftime("%Y-%m-%d")
                query += f" after:{date_filter}"

            if input.search_type == "news":
                query = f"news {query}"
            elif input.search_type == "academic":
                query = f"research paper {query}"

            results = []

            # Try Google Search first
            if self.google_search:
                try:
                    search_results = self.google_search.results(
                        query,
                        num_results=input.num_results
                    )
                    for result in search_results:
                        results.append({
                            "title": result.get("title"),
                            "url": result.get("link"),
                            "snippet": result.get("snippet"),
                            "source": "google",
                        })
                except Exception as e:
                    logger.error(f"Google search failed: {e}")

            # Fallback to DuckDuckGo if needed
            if not results and self.ddg_search:
                try:
                    search_results = self.ddg_search.results(
                        query,
                        num_results=input.num_results
                    )
                    for result in search_results:
                        results.append({
                            "title": result.get("title"),
                            "url": result.get("link"),
                            "snippet": result.get("snippet"),
                            "source": "duckduckgo",
                        })
                except Exception as e:
                    logger.error(f"DuckDuckGo search failed: {e}")

            return {
                "success": bool(results),
                "query": input.query,
                "results": results,
                "total": len(results),
            }

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": [],
            }

    @tool
    def search_documentation(self, input: DocumentationSearchInput) -> Dict[str, Any]:
        """
        Search specific documentation sources.

        Returns:
            Dictionary with documentation results
        """
        # Documentation source URLs
        doc_sources = {
            "langchain": "https://python.langchain.com/docs",
            "langgraph": "https://langchain-ai.github.io/langgraph",
            "openai": "https://platform.openai.com/docs",
            "anthropic": "https://docs.anthropic.com",
            "github": "https://docs.github.com",
            "python": "https://docs.python.org/3",
            "fastapi": "https://fastapi.tiangolo.com",
            "react": "https://react.dev/reference",
            "flutter": "https://docs.flutter.dev",
        }

        base_url = doc_sources.get(input.source.lower())
        if not base_url:
            return {
                "success": False,
                "error": f"Unknown documentation source: {input.source}",
                "results": [],
            }

        # Build search query
        query = f"site:{base_url} {input.query}"
        if input.version:
            query += f" {input.version}"

        # Use web search to find documentation pages
        search_result = self.web_search(
            WebSearchInput(
                query=query,
                num_results=input.num_results
            )
        )

        # Enhance results with documentation context
        results = []
        for result in search_result.get("results", []):
            results.append({
                "title": result["title"],
                "url": result["url"],
                "snippet": result["snippet"],
                "source": input.source,
                "version": input.version,
            })

        return {
            "success": bool(results),
            "source": input.source,
            "query": input.query,
            "results": results,
            "total": len(results),
        }

    @tool
    def summarize_web_page(self, input: WebPageSummaryInput) -> Dict[str, Any]:
        """
        Load and summarize a web page.

        Returns:
            Dictionary with page summary
        """
        try:
            # Load web page
            loader = WebBaseLoader(input.url)
            documents = loader.load()

            if not documents:
                return {
                    "success": False,
                    "error": "Failed to load web page",
                    "summary": None,
                }

            # Extract text content
            content = "\n".join([doc.page_content for doc in documents])

            # Simple extractive summarization
            sentences = content.split(".")
            summary_sentences = []
            word_count = 0

            for sentence in sentences:
                if word_count >= input.max_length:
                    break

                # Check if sentence contains focus areas
                if input.focus_areas:
                    if any(focus.lower() in sentence.lower() for focus in input.focus_areas):
                        summary_sentences.append(sentence.strip())
                        word_count += len(sentence.split())
                else:
                    summary_sentences.append(sentence.strip())
                    word_count += len(sentence.split())

            summary = ". ".join(summary_sentences[:10])  # Limit to 10 sentences

            return {
                "success": True,
                "url": input.url,
                "title": documents[0].metadata.get("title", ""),
                "summary": summary,
                "word_count": word_count,
                "focus_areas": input.focus_areas,
            }

        except Exception as e:
            logger.error(f"Failed to summarize web page: {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": None,
            }

    @tool
    def github_search(self, input: GitHubSearchInput) -> Dict[str, Any]:
        """
        Search GitHub repositories, code, issues, or users.

        Returns:
            Dictionary with GitHub search results
        """
        if not self.github_token:
            return {
                "success": False,
                "error": "GitHub token not configured",
                "results": [],
            }

        # GitHub API endpoints
        endpoints = {
            "repositories": "https://api.github.com/search/repositories",
            "code": "https://api.github.com/search/code",
            "issues": "https://api.github.com/search/issues",
            "users": "https://api.github.com/search/users",
        }

        endpoint = endpoints.get(input.search_type)
        if not endpoint:
            return {
                "success": False,
                "error": f"Invalid search type: {input.search_type}",
                "results": [],
            }

        # Build query
        query = input.query
        if input.language and input.search_type in ["repositories", "code"]:
            query += f" language:{input.language}"

        # Make request
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        params = {
            "q": query,
            "sort": input.sort if input.search_type == "repositories" else None,
            "per_page": min(input.num_results, 100),
        }

        try:
            response = requests.get(
                endpoint,
                headers=headers,
                params=params,
                timeout=10,
            )
            response.raise_for_status()

            data = response.json()
            results = []

            for item in data.get("items", [])[:input.num_results]:
                if input.search_type == "repositories":
                    results.append({
                        "name": item["full_name"],
                        "description": item["description"],
                        "url": item["html_url"],
                        "stars": item["stargazers_count"],
                        "language": item["language"],
                        "updated": item["updated_at"],
                    })
                elif input.search_type == "code":
                    results.append({
                        "file": item["name"],
                        "path": item["path"],
                        "repository": item["repository"]["full_name"],
                        "url": item["html_url"],
                    })
                elif input.search_type == "issues":
                    results.append({
                        "title": item["title"],
                        "state": item["state"],
                        "repository": item["repository_url"].split("/")[-2:],
                        "url": item["html_url"],
                        "created": item["created_at"],
                    })
                elif input.search_type == "users":
                    results.append({
                        "username": item["login"],
                        "url": item["html_url"],
                        "type": item["type"],
                    })

            return {
                "success": True,
                "search_type": input.search_type,
                "query": input.query,
                "results": results,
                "total": data.get("total_count", len(results)),
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": [],
            }


# Export tool functions
def get_search_tools(
    google_api_key: Optional[str] = None,
    google_cse_id: Optional[str] = None,
    github_token: Optional[str] = None,
) -> List:
    """Get list of search tools for agent use."""
    tools = SearchTools(google_api_key, google_cse_id, github_token)
    return [
        tools.web_search,
        tools.search_documentation,
        tools.summarize_web_page,
        tools.github_search,
    ]