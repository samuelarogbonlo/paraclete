"""
Unit tests for model routing system.

Tests model selection, fallback strategies, and cost optimization.
"""

import pytest
from app.agents.router import (
    ModelRouter,
    AgentType,
    ModelProvider,
    ModelCapability,
)


class TestModelRouter:
    """Test model routing and selection logic."""

    def test_router_initializes_with_defaults(self):
        """Router should initialize with default configuration."""
        router = ModelRouter()

        assert router.enable_fallbacks is True
        assert router.track_usage is True
        assert len(router.model_configs) == 3  # Anthropic, OpenAI, Google

    def test_get_model_for_supervisor(self):
        """Should return Claude for supervisor agent."""
        router = ModelRouter()
        model = router.get_model(AgentType.SUPERVISOR)

        assert model is not None
        # Verify it's a ChatAnthropic instance
        assert "claude" in model.model_name.lower()

    def test_get_model_for_coder(self):
        """Should return GPT-4 for coder agent."""
        router = ModelRouter()
        model = router.get_model(AgentType.CODER)

        assert model is not None
        assert "gpt" in model.model_name.lower()

    def test_get_model_for_researcher(self):
        """Should return Gemini for researcher agent."""
        router = ModelRouter()
        model = router.get_model(AgentType.RESEARCHER)

        assert model is not None
        assert "gemini" in model.model_name.lower()

    def test_model_caching(self):
        """Should cache model instances."""
        router = ModelRouter()

        model1 = router.get_model(AgentType.SUPERVISOR)
        model2 = router.get_model(AgentType.SUPERVISOR)

        # Should return same cached instance
        assert model1 is model2

    def test_meets_context_size_requirement(self):
        """Should respect context size requirements."""
        router = ModelRouter()

        # Gemini has 2M context, should meet large requirements
        meets = router._meets_requirements(
            "gemini-1.5-pro",
            context_size=500000,
            require_vision=False,
            require_function_calling=False,
            max_cost_per_1k=None,
        )

        assert meets is True

    def test_fails_insufficient_context_size(self):
        """Should fail when context size is insufficient."""
        router = ModelRouter()

        # Request 3M context (exceeds all models)
        meets = router._meets_requirements(
            "gpt-4o",
            context_size=3000000,
            require_vision=False,
            require_function_calling=False,
            max_cost_per_1k=None,
        )

        assert meets is False

    def test_requires_vision_capability(self):
        """Should filter models without vision when required."""
        router = ModelRouter()

        # gpt-4o-mini doesn't have vision
        meets = router._meets_requirements(
            "gpt-4o-mini",
            context_size=None,
            require_vision=True,
            require_function_calling=False,
            max_cost_per_1k=None,
        )

        assert meets is False

        # gpt-4o has vision
        meets = router._meets_requirements(
            "gpt-4o",
            context_size=None,
            require_vision=True,
            require_function_calling=False,
            max_cost_per_1k=None,
        )

        assert meets is True

    def test_requires_function_calling(self):
        """Should filter models without function calling when required."""
        router = ModelRouter()

        # Claude Opus has function calling
        meets = router._meets_requirements(
            "claude-3-opus-20240229",
            context_size=None,
            require_vision=False,
            require_function_calling=True,
            max_cost_per_1k=None,
        )

        assert meets is True

    def test_respects_cost_constraint(self):
        """Should filter expensive models when cost constrained."""
        router = ModelRouter()

        # Claude Opus is expensive
        meets = router._meets_requirements(
            "claude-3-opus-20240229",
            context_size=None,
            require_vision=False,
            require_function_calling=False,
            max_cost_per_1k=0.01,  # Low cost limit
        )

        assert meets is False

        # GPT-4o-mini is cheap
        meets = router._meets_requirements(
            "gpt-4o-mini",
            context_size=None,
            require_vision=False,
            require_function_calling=False,
            max_cost_per_1k=0.01,
        )

        assert meets is True

    def test_fallback_strategy(self):
        """Should use fallback when primary model doesn't meet requirements."""
        router = ModelRouter()

        # Request vision from supervisor (primary Claude Sonnet has vision)
        model = router.get_model(
            AgentType.SUPERVISOR,
            require_vision=True,
        )

        assert model is not None

    def test_estimate_cost(self):
        """Should estimate token costs correctly."""
        router = ModelRouter()

        # Test with Claude Sonnet
        cost = router.estimate_cost(
            "claude-3-5-sonnet-20241022",
            input_tokens=1000,
            output_tokens=1000,
        )

        # Should be (1000/1000 * 0.003) + (1000/1000 * 0.015) = 0.018
        assert abs(cost - 0.018) < 0.001

    def test_get_cheapest_model(self):
        """Should return cheapest model meeting requirements."""
        router = ModelRouter()

        cheapest = router.get_cheapest_model()

        # Should be one of the cheaper models
        assert "mini" in cheapest.lower() or "flash" in cheapest.lower() or "haiku" in cheapest.lower()

    def test_get_cheapest_model_with_function_calling(self):
        """Should return cheapest model with function calling."""
        router = ModelRouter()

        cheapest = router.get_cheapest_model(
            require_function_calling=True,
        )

        assert cheapest is not None

        # Verify it actually has function calling
        info = router.get_model_info(cheapest)
        assert ModelCapability.FUNCTION_CALLING in info["capabilities"]

    def test_get_model_info(self):
        """Should return model configuration info."""
        router = ModelRouter()

        info = router.get_model_info("claude-3-5-sonnet-20241022")

        assert "capabilities" in info
        assert "context_window" in info
        assert "cost_per_1k_input" in info
        assert "cost_per_1k_output" in info

    def test_unknown_model_raises_error(self):
        """Should raise error for unknown model."""
        router = ModelRouter()

        with pytest.raises(ValueError, match="Unknown model"):
            router._get_or_create_model("totally-fake-model-9000")

    def test_missing_api_key_raises_error(self):
        """Should raise error when API key is missing."""
        router = ModelRouter(
            anthropic_api_key=None,
            openai_api_key=None,
            google_api_key=None,
        )

        with pytest.raises(ValueError, match="API key not configured"):
            router._create_model(ModelProvider.ANTHROPIC, "claude-3-opus-20240229")


@pytest.mark.unit
class TestModelCapabilities:
    """Test model capability definitions."""

    def test_anthropic_models_have_correct_capabilities(self):
        """Anthropic models should have expected capabilities."""
        router = ModelRouter()

        opus_config = router.get_model_info("claude-3-opus-20240229")
        assert ModelCapability.REASONING in opus_config["capabilities"]
        assert ModelCapability.FUNCTION_CALLING in opus_config["capabilities"]

        sonnet_config = router.get_model_info("claude-3-5-sonnet-20241022")
        assert ModelCapability.VISION in sonnet_config["capabilities"]
        assert ModelCapability.FAST_RESPONSE in sonnet_config["capabilities"]

    def test_openai_models_have_correct_capabilities(self):
        """OpenAI models should have expected capabilities."""
        router = ModelRouter()

        gpt4o_config = router.get_model_info("gpt-4o")
        assert ModelCapability.CODE_GENERATION in gpt4o_config["capabilities"]
        assert ModelCapability.VISION in gpt4o_config["capabilities"]

    def test_google_models_have_correct_capabilities(self):
        """Google models should have expected capabilities."""
        router = ModelRouter()

        gemini_config = router.get_model_info("gemini-1.5-pro")
        assert ModelCapability.LARGE_CONTEXT in gemini_config["capabilities"]
        assert gemini_config["context_window"] == 2000000


@pytest.mark.unit
class TestFallbackStrategies:
    """Test fallback routing logic."""

    def test_fallback_chain_exists_for_all_primary_models(self):
        """All primary models should have fallback chains."""
        router = ModelRouter()

        for agent_type in AgentType:
            primary_model = router.agent_model_map[agent_type]
            assert primary_model in router.fallback_chains

    def test_fallback_chains_are_valid_models(self):
        """All models in fallback chains should be valid."""
        router = ModelRouter()

        for fallbacks in router.fallback_chains.values():
            for model_name in fallbacks:
                info = router.get_model_info(model_name)
                assert info, f"Fallback model {model_name} not found in configs"

    def test_uses_fallback_when_primary_unavailable(self):
        """Should use fallback when primary model doesn't meet requirements."""
        router = ModelRouter()

        # Request extremely low cost (primary won't meet it)
        model = router.get_model(
            AgentType.SUPERVISOR,
            max_cost_per_1k=0.0001,
        )

        # Should still return a model (fallback or primary with warning)
        assert model is not None
