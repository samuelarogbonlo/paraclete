"""
Designer agent specializing in architecture, system design, and UI/UX.

Uses GPT-4 for balanced design and architectural decisions.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import json

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.types import Command

from app.agents.state import AgentState, AgentOutput
from app.agents.router import ModelRouter, AgentType

logger = logging.getLogger(__name__)


DESIGNER_SYSTEM_PROMPT = """You are an expert system design and architecture AI agent.
Your role is to:
1. Design scalable and maintainable system architectures
2. Create clear architectural diagrams and documentation
3. Recommend design patterns and best practices
4. Plan database schemas and API designs
5. Design user interfaces and user experiences
6. Consider non-functional requirements (performance, security, scalability)

Focus on:
- Clean architecture principles
- SOLID principles
- Domain-driven design
- Microservices vs monolithic trade-offs
- Technology selection and justification
- Cost-effectiveness and operational complexity

Provide practical, implementable designs with clear rationale.
"""


class DesignArtifact:
    """Container for design artifacts and decisions."""

    def __init__(self):
        self.architecture_decisions: List[Dict] = []
        self.design_patterns: List[str] = []
        self.technology_stack: Dict[str, str] = {}
        self.api_specifications: List[Dict] = []
        self.database_schema: Dict = {}
        self.ui_components: List[Dict] = []
        self.diagrams: List[Dict] = []
        self.non_functional_requirements: Dict = {}

    def add_decision(self, title: str, description: str, rationale: str, alternatives: List[str] = None):
        """Add an architectural decision record (ADR)."""
        self.architecture_decisions.append({
            "title": title,
            "description": description,
            "rationale": rationale,
            "alternatives": alternatives or [],
            "timestamp": datetime.now().isoformat(),
        })

    def add_api_spec(self, endpoint: str, method: str, description: str, request_schema: Dict, response_schema: Dict):
        """Add API specification."""
        self.api_specifications.append({
            "endpoint": endpoint,
            "method": method,
            "description": description,
            "request_schema": request_schema,
            "response_schema": response_schema,
        })

    def add_diagram(self, name: str, type: str, description: str, mermaid_code: Optional[str] = None):
        """Add a diagram specification."""
        self.diagrams.append({
            "name": name,
            "type": type,  # e.g., "architecture", "sequence", "erd", "component"
            "description": description,
            "mermaid_code": mermaid_code,  # Mermaid diagram syntax
        })

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "architecture_decisions": self.architecture_decisions,
            "design_patterns": self.design_patterns,
            "technology_stack": self.technology_stack,
            "api_specifications": self.api_specifications,
            "database_schema": self.database_schema,
            "ui_components": self.ui_components,
            "diagrams": self.diagrams,
            "non_functional_requirements": self.non_functional_requirements,
        }


def designer_node(state: AgentState) -> Command:
    """
    Designer agent that creates system designs and architecture.

    Uses GPT-4 for balanced design capabilities.
    """
    logger.info(f"Designer agent processing task for session {state['session_id']}")

    # Initialize model
    router = ModelRouter()
    model = router.get_model(AgentType.DESIGNER)

    # Get task description
    task = state.get("task_description", "")
    if not task:
        messages = state.get("messages", [])
        if messages:
            task = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])

    # Determine design focus
    design_focus = determine_design_focus(task)

    # Create design prompt based on focus
    prompt_template = get_design_prompt(design_focus)
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=DESIGNER_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
        ("human", prompt_template),
    ])

    try:
        # Execute design task
        chain = prompt | model

        # Get context
        existing_messages = state.get("messages", [])
        project_name = state.get("project_name", "Project")
        research_summary = state.get("research_summary", "")

        response = chain.invoke({
            "messages": existing_messages,
            "task": task,
            "project_name": project_name,
            "research_context": research_summary,
            "focus": design_focus,
        })

        # Process design response into artifacts
        design = process_design_response(response, design_focus)

        # Generate diagrams if applicable
        if design_focus in ["architecture", "database", "system"]:
            generate_design_diagrams(design, task)

        # Create output
        output = AgentOutput(
            agent_name="designer",
            timestamp=datetime.now(),
            result={
                "design": design.to_dict(),
                "focus": design_focus,
                "task": task,
            },
            model_used=model.model_name if hasattr(model, 'model_name') else "gpt-4o",
            tokens_used=None,
            error=None,
        )

        # Generate design summary
        summary = generate_design_summary(design, design_focus)

        # Create response message
        design_message = AIMessage(
            content=summary,
            metadata={
                "agent": "designer",
                "model": output["model_used"],
                "timestamp": datetime.now().isoformat(),
                "design_focus": design_focus,
                "artifacts_created": len(design.diagrams) + len(design.api_specifications),
            }
        )

        # Update state
        state_update = {
            "messages": [design_message],
            "agent_outputs": state.get("agent_outputs", []) + [output],
            "architecture_decisions": design.architecture_decisions,
            "design_patterns": design.design_patterns,
            "system_diagrams": design.diagrams,
            "current_agent": None,
            "agent_statuses": {
                **state.get("agent_statuses", {}),
                "designer": "completed",
            },
        }

        # Determine next step
        if state.get("requires_approval"):
            next_node = "approval"
        elif design_focus == "architecture" and not state.get("skip_implementation"):
            next_node = "coder"  # Send to coder for implementation
        elif state.get("subtasks"):
            next_node = "result_aggregator"
        else:
            next_node = "END"

        return Command(
            goto=next_node,
            update=state_update,
        )

    except Exception as e:
        logger.error(f"Designer agent failed: {e}")

        error_output = AgentOutput(
            agent_name="designer",
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
                "errors": state.get("errors", []) + [{"agent": "designer", "error": str(e)}],
                "agent_statuses": {
                    **state.get("agent_statuses", {}),
                    "designer": "failed",
                },
            }
        )


def determine_design_focus(task: str) -> str:
    """Determine the primary focus of the design task."""
    task_lower = task.lower()

    if any(word in task_lower for word in ["architecture", "system design", "microservice"]):
        return "architecture"
    elif any(word in task_lower for word in ["database", "schema", "model", "entity"]):
        return "database"
    elif any(word in task_lower for word in ["api", "endpoint", "rest", "graphql"]):
        return "api"
    elif any(word in task_lower for word in ["ui", "ux", "interface", "component", "screen"]):
        return "ui_ux"
    elif any(word in task_lower for word in ["flow", "process", "workflow", "sequence"]):
        return "workflow"
    else:
        return "system"  # General system design


def get_design_prompt(focus: str) -> str:
    """Get specialized prompt based on design focus."""
    prompts = {
        "architecture": """Design the system architecture for:
{task}

Project: {project_name}
Research Context: {research_context}

Provide:
1. High-level architecture overview
2. Component breakdown and responsibilities
3. Technology stack recommendations with justification
4. Data flow and integration points
5. Deployment architecture
6. Scalability and reliability considerations
7. Security architecture
8. Cost estimates and trade-offs
""",
        "database": """Design the database schema for:
{task}

Project: {project_name}
Research Context: {research_context}

Provide:
1. Entity relationship diagram
2. Table structures with fields and types
3. Indexes and constraints
4. Data normalization decisions
5. Partitioning and sharding strategy if needed
6. Migration plan from existing schema if applicable
7. Performance optimization considerations
""",
        "api": """Design the API specification for:
{task}

Project: {project_name}
Research Context: {research_context}

Provide:
1. RESTful endpoints or GraphQL schema
2. Request/response formats
3. Authentication and authorization approach
4. Rate limiting and throttling
5. Versioning strategy
6. Error handling standards
7. API documentation approach
8. Integration examples
""",
        "ui_ux": """Design the user interface and experience for:
{task}

Project: {project_name}
Research Context: {research_context}

Provide:
1. User journey and flow
2. Screen/component hierarchy
3. Key UI components and their behavior
4. Design system recommendations
5. Accessibility considerations
6. Mobile responsiveness approach
7. Performance optimization for UI
8. User feedback and error handling
""",
        "workflow": """Design the workflow/process for:
{task}

Project: {project_name}
Research Context: {research_context}

Provide:
1. Process flow diagram
2. State transitions
3. Decision points and branching logic
4. Error handling and rollback procedures
5. Monitoring and alerting points
6. Performance metrics
7. Integration with existing workflows
""",
        "system": """Design the system for:
{task}

Project: {project_name}
Research Context: {research_context}

Provide:
1. System overview and objectives
2. Functional requirements breakdown
3. Non-functional requirements
4. Technology choices and rationale
5. Development approach and phases
6. Testing strategy
7. Deployment and operations plan
8. Risk analysis and mitigation
""",
    }

    return prompts.get(focus, prompts["system"])


def process_design_response(response, focus: str) -> DesignArtifact:
    """Process model response into design artifacts."""
    design = DesignArtifact()

    if not hasattr(response, 'content'):
        return design

    content = response.content

    # Extract design patterns mentioned
    pattern_keywords = [
        "singleton", "factory", "observer", "strategy", "adapter",
        "decorator", "mvc", "mvvm", "repository", "cqrs", "event sourcing",
        "microservices", "layered", "hexagonal", "clean architecture"
    ]
    for pattern in pattern_keywords:
        if pattern in content.lower():
            design.design_patterns.append(pattern.title())

    # Extract technology recommendations
    tech_keywords = {
        "frontend": ["react", "vue", "angular", "flutter", "swift", "kotlin"],
        "backend": ["python", "node", "java", "go", "rust", "c#"],
        "database": ["postgresql", "mysql", "mongodb", "redis", "elasticsearch"],
        "infrastructure": ["aws", "gcp", "azure", "kubernetes", "docker"],
    }
    for category, keywords in tech_keywords.items():
        for keyword in keywords:
            if keyword in content.lower():
                design.technology_stack[category] = keyword.title()

    # Add architectural decision based on content
    if "architecture" in focus:
        design.add_decision(
            title=f"{focus.title()} Design Decision",
            description=content[:500],  # First 500 chars as description
            rationale="Based on requirements analysis and best practices",
            alternatives=[]
        )

    return design


def generate_design_diagrams(design: DesignArtifact, task: str):
    """Generate diagram specifications for the design."""
    # Add architecture diagram
    if design.architecture_decisions:
        mermaid_architecture = """graph TB
    Client[Client Layer]
    API[API Gateway]
    Services[Service Layer]
    Data[Data Layer]

    Client --> API
    API --> Services
    Services --> Data

    style Client fill:#f9f,stroke:#333,stroke-width:2px
    style API fill:#bbf,stroke:#333,stroke-width:2px
    style Services fill:#bfb,stroke:#333,stroke-width:2px
    style Data fill:#fbb,stroke:#333,stroke-width:2px"""

        design.add_diagram(
            name="System Architecture",
            type="architecture",
            description="High-level system architecture diagram",
            mermaid_code=mermaid_architecture
        )

    # Add sequence diagram for workflows
    if "workflow" in task.lower() or "process" in task.lower():
        mermaid_sequence = """sequenceDiagram
    participant User
    participant System
    participant Database

    User->>System: Request
    System->>Database: Query
    Database-->>System: Data
    System-->>User: Response"""

        design.add_diagram(
            name="Process Flow",
            type="sequence",
            description="Sequence diagram showing process flow",
            mermaid_code=mermaid_sequence
        )


def generate_design_summary(design: DesignArtifact, focus: str) -> str:
    """Generate human-readable design summary."""
    design_dict = design.to_dict()
    summary_parts = [f"## {focus.replace('_', ' ').title()} Design Summary\n"]

    # Architecture decisions
    if design_dict["architecture_decisions"]:
        summary_parts.append("### Key Design Decisions")
        for decision in design_dict["architecture_decisions"][:3]:
            summary_parts.append(f"- **{decision['title']}**: {decision['description'][:200]}...")

    # Technology stack
    if design_dict["technology_stack"]:
        summary_parts.append("\n### Technology Stack")
        for category, tech in design_dict["technology_stack"].items():
            summary_parts.append(f"- **{category.title()}**: {tech}")

    # Design patterns
    if design_dict["design_patterns"]:
        summary_parts.append("\n### Design Patterns")
        summary_parts.append(f"- {', '.join(design_dict['design_patterns'][:5])}")

    # API specifications
    if design_dict["api_specifications"]:
        summary_parts.append(f"\n### API Design")
        summary_parts.append(f"- Defined {len(design_dict['api_specifications'])} endpoints")

    # Diagrams
    if design_dict["diagrams"]:
        summary_parts.append(f"\n### Design Artifacts")
        for diagram in design_dict["diagrams"]:
            summary_parts.append(f"- {diagram['name']}: {diagram['description']}")

    # Non-functional requirements
    if design_dict["non_functional_requirements"]:
        summary_parts.append("\n### Non-Functional Requirements")
        for req, value in list(design_dict["non_functional_requirements"].items())[:3]:
            summary_parts.append(f"- **{req}**: {value}")

    return "\n".join(summary_parts)