"""
ATLAS AI Provider Factory

Creates the configured AI adapter for ATLAS.
"""

from atlas.core.config import AtlasConfig


class AIProviderFactory:
    """Create the configured AI provider adapter."""

    SUPPORTED_PROVIDERS = (
        "openai",
        "ollama",
    )

    @classmethod
    def create(
        cls,
        config: AtlasConfig | None = None,
    ):
        """Create an AI adapter from ATLAS configuration."""

        config = config or AtlasConfig()

        provider = getattr(
            config,
            "ai_provider",
            "openai",
        ).lower()

        language = getattr(
            config,
            "language",
            "en",
        )

        if provider == "openai":
            from atlas.adapters.ai import AIAdapter

            try:
                return AIAdapter(
                    language=language,
                )
            except TypeError:
                # Compatibility with simple test/fake adapters.
                return AIAdapter()

        if provider == "ollama":
            from atlas.adapters.ollama import OllamaAdapter

            try:
                return OllamaAdapter(
                    language=language,
                )
            except TypeError:
                # Compatibility with simple test/fake adapters.
                return OllamaAdapter()

        raise ValueError(
            f"Unsupported AI provider: {provider}. "
            "Use 'openai' or 'ollama'."
        )
