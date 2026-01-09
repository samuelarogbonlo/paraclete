"""
Coder agent specializing in code generation, debugging, and refactoring.

Uses GPT-4 for fast and efficient code generation.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import re

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.types import Command

from app.agents.state import AgentState, AgentOutput, GitChange
from app.agents.router import ModelRouter, AgentType
from app.agents.tools.file_tools import get_file_tools
from app.agents.tools.git_tools import get_git_tools

logger = logging.getLogger(__name__)


CODER_SYSTEM_PROMPT = """You are an expert software development AI agent.
Your role is to:
1. Generate high-quality, production-ready code
2. Follow best practices and design patterns
3. Write comprehensive tests when appropriate
4. Add clear documentation and comments
5. Handle errors gracefully with proper error messages
6. Optimize for readability and maintainability

Always consider:
- Security implications
- Performance characteristics
- Code reusability
- Testing requirements
- Documentation needs

You have access to file system and git tools to read, write, and manage code.
"""


def coder_node(state: AgentState) -> Command:
    """
    Coder agent that generates, modifies, and refactors code.

    Uses GPT-4 for fast code generation.
    """
    logger.info(f"Coder agent processing task for session {state['session_id']}")

    # Initialize model and tools
    router = ModelRouter()
    model = router.get_model(
        AgentType.CODER,
        require_function_calling=True,  # Need for tool usage
    )

    # Get workspace path
    workspace_path = state.get("vm_workspace_path", "/tmp/workspace")

    # Get file and git tools
    file_tools = get_file_tools(workspace_root=workspace_path)
    git_tools = get_git_tools(github_token=state.get("github_token"))
    all_tools = file_tools + git_tools

    # Bind tools to model
    model_with_tools = model.bind_tools(all_tools)

    # Get task description
    task = state.get("task_description", "")
    task_type = state.get("task_type", "code_generation")

    if not task:
        messages = state.get("messages", [])
        if messages:
            task = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])

    # Create coding prompt based on task type
    if task_type == "debugging":
        prompt_template = DEBUGGING_PROMPT
    elif task_type == "refactoring":
        prompt_template = REFACTORING_PROMPT
    else:
        prompt_template = CODE_GENERATION_PROMPT

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=CODER_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
        ("human", prompt_template),
    ])

    try:
        # Execute coding task with tools
        chain = prompt | model_with_tools

        # Get context from state
        existing_messages = state.get("messages", [])
        repo_url = state.get("repo_url")
        branch_name = state.get("branch_name", "main")

        response = chain.invoke({
            "messages": existing_messages,
            "task": task,
            "repo_url": repo_url or "No repository specified",
            "branch": branch_name,
            "workspace": workspace_path,
        })

        # Track file changes
        file_changes = []
        tool_results = []

        # Process tool calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                # Find and execute the tool
                for tool in all_tools:
                    if tool.name == tool_name:
                        result = tool.invoke(tool_args)
                        tool_results.append({
                            "tool": tool_name,
                            "args": tool_args,
                            "result": result,
                        })

                        # Track file changes
                        if tool_name in ["write_file", "delete_file"]:
                            file_changes.append(
                                GitChange(
                                    file_path=tool_args.get("file_path", tool_args.get("path", "")),
                                    operation="delete" if tool_name == "delete_file" else "modify",
                                    old_content=None,  # Would need to read first
                                    new_content=tool_args.get("content") if tool_name == "write_file" else None,
                                    diff=None,  # Generated later
                                )
                            )
                        break

        # Generate code summary
        summary = generate_code_summary(response, tool_results, file_changes)

        # Create output
        output = AgentOutput(
            agent_name="coder",
            timestamp=datetime.now(),
            result={
                "summary": summary,
                "files_changed": [change["file_path"] for change in file_changes],
                "tool_calls": tool_results,
                "task": task,
                "task_type": task_type,
            },
            model_used=model.model_name if hasattr(model, 'model_name') else "gpt-4o",
            tokens_used=None,  # Would need token counting
            error=None,
        )

        # Create response message
        code_message = AIMessage(
            content=summary,
            metadata={
                "agent": "coder",
                "model": output["model_used"],
                "timestamp": datetime.now().isoformat(),
                "files_changed": len(file_changes),
            }
        )

        # Update state
        state_update = {
            "messages": [code_message],
            "agent_outputs": state.get("agent_outputs", []) + [output],
            "pending_changes": state.get("pending_changes", []) + file_changes,
            "current_agent": None,
            "agent_statuses": {
                **state.get("agent_statuses", {}),
                "coder": "completed",
            },
        }

        # Determine next step
        if file_changes and state.get("requires_approval"):
            next_node = "approval"
        elif task_type == "code_generation" and not state.get("skip_review"):
            next_node = "reviewer"  # Send to reviewer for code review
        elif state.get("subtasks"):
            next_node = "result_aggregator"
        else:
            next_node = "END"

        return Command(
            goto=next_node,
            update=state_update,
        )

    except Exception as e:
        logger.error(f"Coder agent failed: {e}")

        error_output = AgentOutput(
            agent_name="coder",
            timestamp=datetime.now(),
            result=None,
            model_used="gpt-4o",
            tokens_used=None,
            error=str(e),
        )

        return Command(
            goto="error_handler",
            update={
                "agent_outputs": state.get("agent_outputs", []) + [error_output],
                "errors": state.get("errors", []) + [{"agent": "coder", "error": str(e)}],
                "agent_statuses": {
                    **state.get("agent_statuses", {}),
                    "coder": "failed",
                },
            }
        )


# Specialized prompts for different coding tasks
CODE_GENERATION_PROMPT = """Generate code for the following task:
{task}

Repository: {repo_url}
Branch: {branch}
Workspace: {workspace}

Requirements:
1. Write clean, well-documented code
2. Follow the project's existing patterns and style
3. Include error handling
4. Add tests if appropriate
5. Update any affected documentation
"""

DEBUGGING_PROMPT = """Debug and fix the following issue:
{task}

Repository: {repo_url}
Branch: {branch}
Workspace: {workspace}

Steps:
1. Identify the root cause of the issue
2. Read relevant files to understand the context
3. Implement a fix
4. Test the fix if possible
5. Document what was wrong and how it was fixed
"""

REFACTORING_PROMPT = """Refactor the code for the following improvement:
{task}

Repository: {repo_url}
Branch: {branch}
Workspace: {workspace}

Guidelines:
1. Preserve existing functionality
2. Improve code structure and readability
3. Apply appropriate design patterns
4. Reduce complexity where possible
5. Update tests and documentation as needed
"""


def generate_code_summary(response, tool_results: List[Dict], file_changes: List[GitChange]) -> str:
    """Generate a summary of code changes."""
    summary_parts = []

    # Add main response
    if hasattr(response, 'content'):
        summary_parts.append(response.content)

    # Add file change summary
    if file_changes:
        summary_parts.append("\n**Files Changed:**")
        for change in file_changes:
            operation_symbol = {
                "create": "+",
                "modify": "~",
                "delete": "-",
            }.get(change["operation"], "?")
            summary_parts.append(f"{operation_symbol} {change['file_path']}")

    # Add tool execution summary
    if tool_results:
        successful_tools = [r for r in tool_results if r["result"].get("success")]
        if successful_tools:
            summary_parts.append(f"\n**Tools Executed:** {len(successful_tools)} successful operations")

    return "\n".join(summary_parts)