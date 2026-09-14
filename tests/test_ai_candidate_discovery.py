import json

from atlas.adapters.ai import AIAdapter


def test_ai_adapter_discover_candidates_returns_list(monkeypatch):
    adapter = object.__new__(AIAdapter)
    adapter.model = "test-model"
    adapter.client = type(
        "Client",
        (),
        {
            "responses": type(
                "Responses",
                (),
                {
                    "create": lambda self, **kwargs: type(
                        "Response",
                        (),
                        {
                            "output_text": json.dumps(
                                [
                                    {
                                        "symbol": "NVDA",
                                        "score": 88,
                                        "reason": "Strong catalyst",
                                        "metadata": {
                                            "asset_type": "stock"
                                        },
                                    }
                                ]
                            )
                        },
                    )()
                },
            )()
        },
    )()

    result = adapter.discover_candidates(
        "NVDA has a significant new catalyst."
    )

    assert result[0]["symbol"] == "NVDA"
    assert result[0]["score"] == 88


def test_ai_adapter_discover_candidates_accepts_wrapped_response():
    adapter = object.__new__(AIAdapter)
    adapter.model = "test-model"
    adapter.client = type(
        "Client",
        (),
        {
            "responses": type(
                "Responses",
                (),
                {
                    "create": lambda self, **kwargs: type(
                        "Response",
                        (),
                        {
                            "output_text": json.dumps(
                                {
                                    "candidates": [
                                        {
                                            "symbol": "BTC-USD",
                                            "score": 81,
                                            "reason": "Crypto catalyst",
                                        }
                                    ]
                                }
                            )
                        },
                    )()
                },
            )()
        },
    )()

    result = adapter.discover_candidates("BTC has a new catalyst.")

    assert len(result) == 1
    assert result[0]["symbol"] == "BTC-USD"


def test_ai_adapter_discover_candidates_returns_empty_for_invalid_shape():
    adapter = object.__new__(AIAdapter)
    adapter.model = "test-model"
    adapter.client = type(
        "Client",
        (),
        {
            "responses": type(
                "Responses",
                (),
                {
                    "create": lambda self, **kwargs: type(
                        "Response",
                        (),
                        {
                            "output_text": "{}"
                        },
                    )()
                },
            )()
        },
    )()

    assert adapter.discover_candidates("No useful evidence.") == []
