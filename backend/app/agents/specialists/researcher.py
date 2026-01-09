"""
Researcher agent specializing in web search and documentation lookup.

Uses Gemini for large context window to process extensive search results.
"""

from typing import Dict, Any, List
from datetime import datetime
import logging

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.types import Command

from app.agents.state import AgentState, AgentOutput
from app.agents.router import ModelRouter, AgentType
from app.agents.tools.search_tools import get_search_tools

logger = logging.getLogger(__name__)


RESEARCHER_SYSTEM_PROMPT = """You are a research specialist AI agent.
Your role is to:
1. Search for relevant information across the web and documentation
2. Synthesize findings into clear, actionable insights
3. Provide sources and citations for all information
4. Identify knowledge gaps and suggest follow-up research

Focus on accuracy, relevance, and comprehensive coverage of the topic.
Always cite your sources and distinguish between facts and speculation.
"""


def researcher_node(state: AgentState) -> Command:
    """
    Researcher agent that performs web search and documentation lookup.

    Uses Gemini model for large context window processing.
    """
    logger.info(f"Researcher agent processing task for session {state['session_id']}")

    # Initialize model and tools
    router = ModelRouter()
    model = router.get_model(
        AgentType.RESEARCHER,
        context_size=100000,  # Request large context for research
    )

    # Get search tools
    search_tools = get_search_tools(
        google_api_key=state.get("google_api_key"),
        github_token=state.get("github_token"),
    )

    # Bind tools to model
    model_with_tools = model.bind_tools(search_tools)

    # Get task description
    task = state.get("task_description", "")
    if not task:
        # Get from latest message
        messages = state.get("messages", [])
        if messages:
            task = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])

    # Create research prompt
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=RESEARCHER_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
        ("human", "Research the following topic and provide comprehensive findings:\n{task}"),
    ])

    try:
        # Execute research with tools
        chain = prompt | model_with_tools

        # Get existing messages for context
        existing_messages = state.get("messages", [])

        response = chain.invoke({
            "messages": existing_messages,
            "task": task,
        })

        # Process tool calls if any
        tool_results = []
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                # Find and execute the tool
                for tool in search_tools:
                    if tool.name == tool_name:
                        result = tool.invoke(tool_args)
                        tool_results.append({
                            "tool": tool_name,
                            "args": tool_args,
                            "result": result,
                        })
                        break

        # Generate final research summary
        summary_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=RESEARCHER_SYSTEM_PROMPT),
            ("human", "Based on the following research results, provide a comprehensive summary:\n{results}"),
        ])

        if tool_results:
            summary_response = summary_prompt | model
            final_response = summary_response.invoke({
                "results": str(tool_results),
            })
        else:
            final_response = response

        # Create output
        output = AgentOutput(
            agent_name="researcher",
            timestamp=datetime.now(),
            result={
                "summary": final_response.content if hasattr(final_response, 'content') else str(final_response),
                "sources": tool_results,
                "task": task,
            },
            model_used=model.model_name if hasattr(model, 'model_name') else "gemini-1.5-pro",
            tokens_used=None,  # Would need token counting
            error=None,
        )

        # Update state
        research_message = AIMessage(
            content=final_response.content if hasattr(final_response, 'content') else str(final_response),
            metadata={
                "agent": "researcher",
                "model": output["model_used"],
                "timestamp": datetime.now().isoformat(),
                "sources": len(tool_results),
            }
        )

        state_update = {
            "messages": [research_message],
            "agent_outputs": state.get("agent_outputs", []) + [output],
            "search_results": tool_results,
            "research_summary": output["result"]["summary"],
            "current_agent": None,
            "agent_statuses": {
                **state.get("agent_statuses", {}),
                "researcher": "completed",
            },
        }

        # Determine next step
        if state.get("requires_approval"):
            next_node = "approval"
        elif state.get("subtasks") and len(state.get("completed_subtasks", [])) < len(state["subtasks"]):
            next_node = "result_aggregator"
        else:
            next_node = "END"

        return Command(
            goto=next_node,
            update=state_update,
        )

    except Exception as e:
        logger.error(f"Researcher agent failed: {e}")

        error_output = AgentOutput(
            agent_name="researcher",
            timestamp=datetime.now(),
            result=None,
            model_used="gemini-1.5-pro",
            tokens_used=None,
            error=str(e),
        )

        return Command(
            goto="error_handler",
            update={
                "agent_outputs": state.get("agent_outputs", []) + [error_output],
                "errors": state.get("errors", []) + [{"agent": "researcher", "error": str(e)}],
                "agent_statuses": {
                    **state.get("agent_statuses", {}),
                    "researcher": "failed",
                },
            }
        )


def research_with_context(
    query: str,
    context: List[str],
    model,
    search_tools: List,
    max_searches: int = 3,
) -> Dict[str, Any]:
    """
    Perform iterative research with context building.

    Args:
        query: Research query
        context: Previous research context
        model: Language model to use
        search_tools: Available search tools
        max_searches: Maximum number of search iterations

    Returns:
        Research results with sources
    """
    all_results = []
    search_queries = [query]  # Start with original query

    for iteration in range(max_searches):
        if not search_queries:
            break

        current_query = search_queries.pop(0)

        # Search with current query
        for tool in search_tools:
            if "web_search" in tool.name:
                results = tool.invoke({
                    "query": current_query,
                    "num_results": 5,
                })
                all_results.append(results)
                break

        # Generate follow-up queries if needed
        if iteration < max_searches - 1:
            follow_up_prompt = ChatPromptTemplate.from_messages([
                ("system", "Based on the research results, suggest follow-up search queries to deepen understanding."),
                ("human", "Results so far: {results}\nOriginal query: {query}"),
            ])

            follow_up_response = follow_up_prompt | model
            response = follow_up_response.invoke({
                "results": str(all_results),
                "query": query,
            })

            # Extract follow-up queries (simple parsing)
            if hasattr(response, 'content'):
                lines = response.content.split("\n")
                for line in lines[:2]:  # Take up to 2 follow-up queries
                    if line.strip():
                        search_queries.append(line.strip())

    return {
        "query": query,
        "iterations": len(all_results),
        "results": all_results,
        "context": context,
    }