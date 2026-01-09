"""
Reviewer agent specializing in code review, security, and quality checks.

Uses Claude for superior reasoning and analysis capabilities.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import re

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.types import Command

from app.agents.state import AgentState, AgentOutput
from app.agents.router import ModelRouter, AgentType
from app.agents.tools.file_tools import get_file_tools
from app.agents.tools.git_tools import get_git_tools

logger = logging.getLogger(__name__)


REVIEWER_SYSTEM_PROMPT = """You are an expert code review AI agent with deep expertise in:
- Security best practices and vulnerability detection
- Performance optimization
- Code quality and maintainability
- Design patterns and architecture
- Testing strategies

Your role is to:
1. Thoroughly review code changes for issues and improvements
2. Identify security vulnerabilities (OWASP Top 10, etc.)
3. Suggest performance optimizations
4. Ensure code follows best practices and standards
5. Verify adequate test coverage
6. Check documentation completeness

Provide constructive feedback with specific suggestions for improvement.
Rate severity of issues as: CRITICAL, HIGH, MEDIUM, LOW, INFO
"""


class CodeReview:
    """Structure for code review findings."""

    def __init__(self):
        self.security_issues: List[Dict] = []
        self.performance_issues: List[Dict] = []
        self.quality_issues: List[Dict] = []
        self.suggestions: List[Dict] = []
        self.positive_feedback: List[str] = []

    def add_issue(
        self,
        category: str,
        severity: str,
        description: str,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        suggestion: Optional[str] = None,
    ):
        """Add an issue to the review."""
        issue = {
            "severity": severity,
            "description": description,
            "file_path": file_path,
            "line_number": line_number,
            "suggestion": suggestion,
            "timestamp": datetime.now().isoformat(),
        }

        if category == "security":
            self.security_issues.append(issue)
        elif category == "performance":
            self.performance_issues.append(issue)
        elif category == "quality":
            self.quality_issues.append(issue)
        else:
            self.suggestions.append(issue)

    def has_critical_issues(self) -> bool:
        """Check if review found critical issues."""
        all_issues = self.security_issues + self.performance_issues + self.quality_issues
        return any(issue["severity"] == "CRITICAL" for issue in all_issues)

    def to_dict(self) -> Dict:
        """Convert review to dictionary."""
        return {
            "security_issues": self.security_issues,
            "performance_issues": self.performance_issues,
            "quality_issues": self.quality_issues,
            "suggestions": self.suggestions,
            "positive_feedback": self.positive_feedback,
            "has_critical_issues": self.has_critical_issues(),
            "total_issues": len(self.security_issues) + len(self.performance_issues) + len(self.quality_issues),
        }


def reviewer_node(state: AgentState) -> Command:
    """
    Reviewer agent that performs code review and quality checks.

    Uses Claude for deep reasoning and analysis.
    """
    logger.info(f"Reviewer agent processing task for session {state['session_id']}")

    # Initialize model and tools
    router = ModelRouter()
    model = router.get_model(
        AgentType.REVIEWER,
        require_function_calling=True,
    )

    # Get workspace path
    workspace_path = state.get("vm_workspace_path", "/tmp/workspace")

    # Get file and git tools
    file_tools = get_file_tools(workspace_root=workspace_path)
    git_tools = get_git_tools(github_token=state.get("github_token"))
    all_tools = file_tools + git_tools

    # Bind tools to model
    model_with_tools = model.bind_tools(all_tools)

    # Get changes to review
    pending_changes = state.get("pending_changes", [])
    files_changed = [change["file_path"] for change in pending_changes]

    # If no explicit changes, look for files mentioned in agent outputs
    if not files_changed:
        agent_outputs = state.get("agent_outputs", [])
        for output in agent_outputs:
            if output.get("result") and isinstance(output["result"], dict):
                files_changed.extend(output["result"].get("files_changed", []))

    # Create review prompt
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=REVIEWER_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
        ("human", REVIEW_PROMPT_TEMPLATE),
    ])

    try:
        # Prepare review context
        review_context = {
            "files_changed": files_changed,
            "pending_changes": pending_changes,
            "task_description": state.get("task_description", ""),
            "task_type": state.get("task_type", ""),
        }

        # Get diff if available
        diff_result = None
        if workspace_path and git_tools:
            for tool in git_tools:
                if tool.name == "get_diff":
                    diff_result = tool.invoke({
                        "workspace_path": workspace_path,
                        "cached": False,
                    })
                    break

        if diff_result and diff_result.get("success"):
            review_context["diff"] = diff_result["diff"]

        # Execute review with tools
        chain = prompt | model_with_tools

        existing_messages = state.get("messages", [])
        response = chain.invoke({
            "messages": existing_messages,
            "context": str(review_context),
            "files": "\n".join(files_changed) if files_changed else "No files specified",
        })

        # Process review findings
        review = process_review_response(response)

        # Read files for detailed analysis if needed
        if files_changed and all_tools:
            for file_path in files_changed[:5]:  # Limit to 5 files for performance
                for tool in file_tools:
                    if tool.name == "read_file":
                        file_content = tool.invoke({"file_path": file_path})
                        if file_content.get("success"):
                            # Analyze file content
                            analyze_file_security(file_content["content"], file_path, review)
                            analyze_file_performance(file_content["content"], file_path, review)
                        break

        # Create output
        output = AgentOutput(
            agent_name="reviewer",
            timestamp=datetime.now(),
            result={
                "review": review.to_dict(),
                "files_reviewed": files_changed,
                "diff_analyzed": bool(diff_result),
            },
            model_used=model.model_name if hasattr(model, 'model_name') else "claude-3-opus",
            tokens_used=None,
            error=None,
        )

        # Generate review summary
        summary = generate_review_summary(review)

        # Create response message
        review_message = AIMessage(
            content=summary,
            metadata={
                "agent": "reviewer",
                "model": output["model_used"],
                "timestamp": datetime.now().isoformat(),
                "issues_found": review.to_dict()["total_issues"],
                "has_critical": review.has_critical_issues(),
            }
        )

        # Update state
        state_update = {
            "messages": [review_message],
            "agent_outputs": state.get("agent_outputs", []) + [output],
            "review_comments": review.to_dict()["quality_issues"] + review.to_dict()["suggestions"],
            "security_issues": review.to_dict()["security_issues"],
            "performance_issues": review.to_dict()["performance_issues"],
            "current_agent": None,
            "agent_statuses": {
                **state.get("agent_statuses", {}),
                "reviewer": "completed",
            },
        }

        # Determine next step based on review findings
        if review.has_critical_issues():
            # Critical issues found - require fixes before proceeding
            state_update["requires_approval"] = True
            next_node = "approval"
        elif state.get("requires_approval"):
            next_node = "approval"
        elif state.get("subtasks"):
            next_node = "result_aggregator"
        else:
            next_node = "END"

        return Command(
            goto=next_node,
            update=state_update,
        )

    except Exception as e:
        logger.error(f"Reviewer agent failed: {e}")

        error_output = AgentOutput(
            agent_name="reviewer",
            timestamp=datetime.now(),
            result=None,
            model_used="claude-3-opus",
            tokens_used=None,
            error=str(e),
        )

        return Command(
            goto="error_handler",
            update={
                "agent_outputs": state.get("agent_outputs", []) + [error_output],
                "errors": state.get("errors", []) + [{"agent": "reviewer", "error": str(e)}],
                "agent_statuses": {
                    **state.get("agent_statuses", {}),
                    "reviewer": "failed",
                },
            }
        )


REVIEW_PROMPT_TEMPLATE = """Review the following code changes:
{context}

Files to review:
{files}

Perform a comprehensive review covering:
1. Security vulnerabilities (SQL injection, XSS, authentication issues, etc.)
2. Performance bottlenecks (N+1 queries, memory leaks, inefficient algorithms)
3. Code quality (duplication, complexity, maintainability)
4. Best practices and design patterns
5. Test coverage and edge cases
6. Documentation and comments

For each issue found, specify:
- Severity: CRITICAL, HIGH, MEDIUM, LOW, INFO
- Description of the issue
- File path and line number if applicable
- Suggested fix or improvement

Also highlight positive aspects of the code.
"""


def process_review_response(response) -> CodeReview:
    """Process model response into structured review."""
    review = CodeReview()

    if not hasattr(response, 'content'):
        return review

    content = response.content
    lines = content.split("\n")

    current_category = None
    current_severity = None

    for line in lines:
        line = line.strip()

        # Detect category headers
        if "security" in line.lower() and ":" in line:
            current_category = "security"
        elif "performance" in line.lower() and ":" in line:
            current_category = "performance"
        elif "quality" in line.lower() and ":" in line:
            current_category = "quality"

        # Detect severity
        severity_match = re.search(r'\b(CRITICAL|HIGH|MEDIUM|LOW|INFO)\b', line)
        if severity_match:
            current_severity = severity_match.group(1)

        # Detect issues (lines starting with - or *)
        if (line.startswith("-") or line.startswith("*")) and current_category:
            description = line[1:].strip()
            if description:
                review.add_issue(
                    category=current_category,
                    severity=current_severity or "MEDIUM",
                    description=description,
                )

        # Detect positive feedback
        if any(keyword in line.lower() for keyword in ["good", "excellent", "well", "positive", "great"]):
            if not any(neg in line.lower() for neg in ["not", "no", "isn't", "wasn't"]):
                review.positive_feedback.append(line)

    return review


def analyze_file_security(content: str, file_path: str, review: CodeReview):
    """Analyze file content for security issues."""
    # SQL injection patterns
    sql_patterns = [
        (r'f["\'].*SELECT.*{.*}', "Potential SQL injection via f-string"),
        (r'\.format\(.*\).*(?:SELECT|INSERT|UPDATE|DELETE)', "Potential SQL injection via format()"),
        (r'%.*(?:SELECT|INSERT|UPDATE|DELETE)', "Potential SQL injection via % formatting"),
    ]

    for pattern, description in sql_patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            review.add_issue(
                category="security",
                severity="HIGH",
                description=description,
                file_path=file_path,
                line_number=line_num,
                suggestion="Use parameterized queries or ORM methods",
            )

    # Hardcoded secrets
    secret_patterns = [
        (r'(?:password|api_key|secret|token)\s*=\s*["\'][\w\-]+["\']', "Potential hardcoded secret"),
        (r'Bearer\s+[\w\-\.]+', "Potential hardcoded bearer token"),
    ]

    for pattern, description in secret_patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            review.add_issue(
                category="security",
                severity="CRITICAL",
                description=description,
                file_path=file_path,
                line_number=line_num,
                suggestion="Use environment variables or secrets management",
            )


def analyze_file_performance(content: str, file_path: str, review: CodeReview):
    """Analyze file content for performance issues."""
    # N+1 query patterns
    if "for" in content and any(orm in content for orm in ["select", "query", "filter", "get"]):
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "for" in line:
                # Check next few lines for database queries
                for j in range(i + 1, min(i + 10, len(lines))):
                    if any(orm in lines[j] for orm in ["select(", "query(", "filter(", "get("]):
                        review.add_issue(
                            category="performance",
                            severity="HIGH",
                            description="Potential N+1 query problem",
                            file_path=file_path,
                            line_number=i + 1,
                            suggestion="Use eager loading or batch queries",
                        )
                        break


def generate_review_summary(review: CodeReview) -> str:
    """Generate human-readable review summary."""
    review_dict = review.to_dict()
    summary_parts = ["## Code Review Summary\n"]

    # Overall assessment
    if review_dict["has_critical_issues"]:
        summary_parts.append("**\u26a0\ufe0f CRITICAL ISSUES FOUND - Immediate attention required**\n")
    elif review_dict["total_issues"] > 0:
        summary_parts.append(f"**Found {review_dict['total_issues']} issues to address**\n")
    else:
        summary_parts.append("**\u2705 Code looks good - No major issues found**\n")

    # Security issues
    if review_dict["security_issues"]:
        summary_parts.append(f"\n### Security Issues ({len(review_dict['security_issues'])})")
        for issue in review_dict["security_issues"][:3]:  # Show top 3
            summary_parts.append(f"- [{issue['severity']}] {issue['description']}")

    # Performance issues
    if review_dict["performance_issues"]:
        summary_parts.append(f"\n### Performance Issues ({len(review_dict['performance_issues'])})")
        for issue in review_dict["performance_issues"][:3]:
            summary_parts.append(f"- [{issue['severity']}] {issue['description']}")

    # Code quality issues
    if review_dict["quality_issues"]:
        summary_parts.append(f"\n### Code Quality Issues ({len(review_dict['quality_issues'])})")
        for issue in review_dict["quality_issues"][:3]:
            summary_parts.append(f"- [{issue['severity']}] {issue['description']}")

    # Positive feedback
    if review_dict["positive_feedback"]:
        summary_parts.append("\n### Positive Aspects")
        for feedback in review_dict["positive_feedback"][:3]:
            summary_parts.append(f"- {feedback}")

    return "\n".join(summary_parts)