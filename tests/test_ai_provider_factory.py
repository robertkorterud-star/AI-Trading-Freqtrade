from atlas.core.config import AtlasConfig
from atlas.core.ai_provider_factory import AIProviderFactory


def test_factory_defaults_to_ollama():

    config = AtlasConfig()

    adapter = AIProviderFactory.create(
        config=config,
    )

    assert adapter.__class__.__name__ == "OllamaAdapter"


def test_factory_creates_ollama_adapter():

    config = AtlasConfig(
        ai_provider="ollama",
        language="no",
    )

    adapter = AIProviderFactory.create(
        config=config,
    )

    assert adapter.__class__.__name__ == "OllamaAdapter"
    assert adapter.language == "no"


def test_factory_creates_openai_adapter():

    config = AtlasConfig(
        ai_provider="openai",
        language="no",
    )

    adapter = AIProviderFactory.create(
        config=config,
    )

    assert adapter.__class__.__name__ == "AIAdapter"
    assert adapter.language == "no"


def test_factory_rejects_unknown_provider():

    config = AtlasConfig(
        ai_provider="unknown",
    )

    try:
        AIProviderFactory.create(
            config=config,
        )
    except ValueError:
        return

    raise AssertionError(
        "Unknown AI provider must be rejected"
    )
