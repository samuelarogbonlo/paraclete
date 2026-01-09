"""
Model routing system for optimal LLM selection per agent type.

This module implements intelligent model selection based on agent requirements:
- Claude: Best reasoning for review and supervision
- GPT-4: Fast generation for coding
- Gemini: Large context window for research
"""

import os
from typing import Optional, Dict, List, Any
from enum import Enum
import logging

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models import BaseChatModel
from langchain_core.callbacks import CallbackManagerForLLMRun

from app.config import settings

logger = logging.getLogger(__name__)


class ModelProvider(str, Enum):
    """Supported model providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"


class AgentType(str, Enum):
    """Agent types for model routing."""

    SUPERVISOR = "supervisor"
    RESEARCHER = "researcher"
    CODER = "coder"
    REVIEWER = "reviewer"
    DESIGNER = "designer"


class ModelCapability(str, Enum):
    """Model capabilities for matching."""

    REASONING = "reasoning"
    CODE_GENERATION = "code_generation"
    LARGE_CONTEXT = "large_context"
    FAST_RESPONSE = "fast_response"
    VISION = "vision"
    FUNCTION_CALLING = "function_calling"


class ModelRouter:
    """
    Routes agent requests to optimal models based on capabilities and requirements.

    Implements fallback strategies and cost optimization.
    """

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        google_api_key: Optional[str] = None,
        enable_fallbacks: bool = True,
        track_usage: bool = True,
    ):
        """Initialize model router with API keys."""
        self.anthropic_api_key = anthropic_api_key or settings.ANTHROPIC_API_KEY
        self.openai_api_key = openai_api_key or settings.OPENAI_API_KEY
        self.google_api_key = google_api_key or settings.GOOGLE_API_KEY

        self.enable_fallbacks = enable_fallbacks
        self.track_usage = track_usage

        # Model configurations
        self.model_configs = {
            ModelProvider.ANTHROPIC: {
                "claude-3-opus-20240229": {
                    "capabilities": [
                        ModelCapability.REASONING,
                        ModelCapability.CODE_GENERATION,
                        ModelCapability.FUNCTION_CALLING,
                    ],
                    "context_window": 200000,
                    "cost_per_1k_input": 0.015,
                    "cost_per_1k_output": 0.075,
                },
                "claude-3-5-sonnet-20241022": {
                    "capabilities": [
                        ModelCapability.REASONING,
                        ModelCapability.CODE_GENERATION,
                        ModelCapability.FAST_RESPONSE,
                        ModelCapability.FUNCTION_CALLING,
                        ModelCapability.VISION,
                    ],
                    "context_window": 200000,
                    "cost_per_1k_input": 0.003,
                    "cost_per_1k_output": 0.015,
                },
                "claude-3-5-haiku-20241022": {
                    "capabilities": [
                        ModelCapability.FAST_RESPONSE,
                        ModelCapability.CODE_GENERATION,
                    ],
                    "context_window": 200000,
                    "cost_per_1k_input": 0.001,
                    "cost_per_1k_output": 0.005,
                },
            },
            ModelProvider.OPENAI: {
                "gpt-4-turbo-preview": {
                    "capabilities": [
                        ModelCapability.CODE_GENERATION,
                        ModelCapability.FAST_RESPONSE,
                        ModelCapability.FUNCTION_CALLING,
                        ModelCapability.VISION,
                    ],
                    "context_window": 128000,
                    "cost_per_1k_input": 0.01,
                    "cost_per_1k_output": 0.03,
                },
                "gpt-4o": {
                    "capabilities": [
                        ModelCapability.REASONING,
                        ModelCapability.CODE_GENERATION,
                        ModelCapability.FAST_RESPONSE,
                        ModelCapability.FUNCTION_CALLING,
                        ModelCapability.VISION,
                    ],
                    "context_window": 128000,
                    "cost_per_1k_input": 0.005,
                    "cost_per_1k_output": 0.015,
                },
                "gpt-4o-mini": {
                    "capabilities": [
                        ModelCapability.FAST_RESPONSE,
                        ModelCapability.CODE_GENERATION,
                    ],
                    "context_window": 128000,
                    "cost_per_1k_input": 0.00015,
                    "cost_per_1k_output": 0.0006,
                },
            },
            ModelProvider.GOOGLE: {
                "gemini-1.5-pro": {
                    "capabilities": [
                        ModelCapability.LARGE_CONTEXT,
                        ModelCapability.REASONING,
                        ModelCapability.CODE_GENERATION,
                        ModelCapability.VISION,
                    ],
                    "context_window": 2000000,  # 2M context
                    "cost_per_1k_input": 0.00125,
                    "cost_per_1k_output": 0.005,
                },
                "gemini-1.5-flash": {
                    "capabilities": [
                        ModelCapability.FAST_RESPONSE,
                        ModelCapability.LARGE_CONTEXT,
                    ],
                    "context_window": 1000000,  # 1M context
                    "cost_per_1k_input": 0.000075,
                    "cost_per_1k_output": 0.0003,
                },
            },
        }

        # Agent to model mapping (primary choices)
        self.agent_model_map = {
            AgentType.SUPERVISOR: "claude-3-5-sonnet-20241022",  # Best reasoning
            AgentType.REVIEWER: "claude-3-opus-20240229",  # Deepest analysis
            AgentType.CODER: "gpt-4o",  # Fast and capable
            AgentType.RESEARCHER: "gemini-1.5-pro",  # Massive context
            AgentType.DESIGNER: "gpt-4o",  # Good balance
        }

        # Fallback chains
        self.fallback_chains = {
            "claude-3-5-sonnet-20241022": ["claude-3-opus-20240229", "gpt-4o", "gemini-1.5-pro"],
            "claude-3-opus-20240229": ["claude-3-5-sonnet-20241022", "gpt-4o"],
            "gpt-4o": ["gpt-4-turbo-preview", "claude-3-5-sonnet-20241022", "gemini-1.5-pro"],
            "gemini-1.5-pro": ["gemini-1.5-flash", "claude-3-5-sonnet-20241022", "gpt-4o"],
        }

        # Initialize model instances cache
        self._model_cache: Dict[str, BaseChatModel] = {}

    def get_model(
        self,
        agent_type: AgentType,
        context_size: Optional[int] = None,
        require_vision: bool = False,
        require_function_calling: bool = False,
        max_cost_per_1k: Optional[float] = None,
    ) -> BaseChatModel:
        """
        Get optimal model for agent type with constraints.

        Args:
            agent_type: Type of agent requesting model
            context_size: Required context window size
            require_vision: Whether vision capabilities are needed
            require_function_calling: Whether function calling is needed
            max_cost_per_1k: Maximum cost constraint per 1k tokens

        Returns:
            Configured LangChain chat model

        Raises:
            ValueError: If no suitable model is available
        """
        # Get primary model for agent type
        primary_model = self.agent_model_map.get(agent_type)
        if not primary_model:
            raise ValueError(f"No model mapping for agent type: {agent_type}")

        # Check if primary model meets requirements
        if self._meets_requirements(
            primary_model, context_size, require_vision, require_function_calling, max_cost_per_1k
        ):
            return self._get_or_create_model(primary_model)

        # Try fallbacks if enabled
        if self.enable_fallbacks:
            fallbacks = self.fallback_chains.get(primary_model, [])
            for fallback_model in fallbacks:
                if self._meets_requirements(
                    fallback_model,
                    context_size,
                    require_vision,
                    require_function_calling,
                    max_cost_per_1k,
                ):
                    logger.info(
                        f"Using fallback model {fallback_model} instead of {primary_model} for {agent_type}"
                    )
                    return self._get_or_create_model(fallback_model)

        # If no suitable model found, return primary anyway with warning
        logger.warning(
            f"No model meets all requirements for {agent_type}, using primary: {primary_model}"
        )
        return self._get_or_create_model(primary_model)

    def _meets_requirements(
        self,
        model_name: str,
        context_size: Optional[int],
        require_vision: bool,
        require_function_calling: bool,
        max_cost_per_1k: Optional[float],
    ) -> bool:
        """Check if model meets specified requirements."""
        # Find model config
        model_config = None
        for provider_models in self.model_configs.values():
            if model_name in provider_models:
                model_config = provider_models[model_name]
                break

        if not model_config:
            return False

        # Check context size
        if context_size and model_config["context_window"] < context_size:
            return False

        # Check capabilities
        capabilities = model_config["capabilities"]
        if require_vision and ModelCapability.VISION not in capabilities:
            return False
        if require_function_calling and ModelCapability.FUNCTION_CALLING not in capabilities:
            return False

        # Check cost constraint
        if max_cost_per_1k:
            avg_cost = (model_config["cost_per_1k_input"] + model_config["cost_per_1k_output"]) / 2
            if avg_cost > max_cost_per_1k:
                return False

        return True

    def _get_or_create_model(self, model_name: str) -> BaseChatModel:
        """Get model from cache or create new instance."""
        if model_name in self._model_cache:
            return self._model_cache[model_name]

        # Determine provider
        provider = None
        for prov, models in self.model_configs.items():
            if model_name in models:
                provider = prov
                break

        if not provider:
            raise ValueError(f"Unknown model: {model_name}")

        # Create model instance
        model = self._create_model(provider, model_name)
        self._model_cache[model_name] = model
        return model

    def _create_model(self, provider: ModelProvider, model_name: str) -> BaseChatModel:
        """Create model instance based on provider."""
        if provider == ModelProvider.ANTHROPIC:
            if not self.anthropic_api_key:
                raise ValueError("Anthropic API key not configured")
            return ChatAnthropic(
                model=model_name,
                anthropic_api_key=self.anthropic_api_key,
                temperature=0.7,
                max_tokens=4096,
            )

        elif provider == ModelProvider.OPENAI:
            if not self.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            return ChatOpenAI(
                model=model_name,
                openai_api_key=self.openai_api_key,
                temperature=0.7,
                max_tokens=4096,
            )

        elif provider == ModelProvider.GOOGLE:
            if not self.google_api_key:
                raise ValueError("Google API key not configured")
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=self.google_api_key,
                temperature=0.7,
                max_output_tokens=4096,
            )

        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get information about a specific model."""
        for provider_models in self.model_configs.values():
            if model_name in provider_models:
                return provider_models[model_name]
        return {}

    def estimate_cost(
        self, model_name: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Estimate cost for token usage."""
        info = self.get_model_info(model_name)
        if not info:
            return 0.0

        input_cost = (input_tokens / 1000) * info["cost_per_1k_input"]
        output_cost = (output_tokens / 1000) * info["cost_per_1k_output"]
        return input_cost + output_cost

    def get_cheapest_model(
        self,
        min_context: int = 0,
        require_vision: bool = False,
        require_function_calling: bool = False,
    ) -> str:
        """Get cheapest model meeting requirements."""
        cheapest = None
        min_cost = float("inf")

        for provider_models in self.model_configs.values():
            for model_name, config in provider_models.items():
                if not self._meets_requirements(
                    model_name, min_context, require_vision, require_function_calling, None
                ):
                    continue

                avg_cost = (config["cost_per_1k_input"] + config["cost_per_1k_output"]) / 2
                if avg_cost < min_cost:
                    min_cost = avg_cost
                    cheapest = model_name

        return cheapest or "gpt-4o-mini"  # Ultimate fallback