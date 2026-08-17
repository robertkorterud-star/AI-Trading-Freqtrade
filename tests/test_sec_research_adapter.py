from unittest.mock import patch

from atlas.adapters.sec_research import SECResearchAdapter


def test_sec_research_returns_company_filings():

    response_data = {
        "name": "NVIDIA CORP",
        "tickers": ["NVDA"],
        "filings": {
            "recent": {
                "form": [
                    "10-Q",
                    "8-K",
                    "10-K",
                ],
                "filingDate": [
                    "2026-08-01",
                    "2026-07-20",
                    "2026-06-01",
                ],
                "accessionNumber": [
                    "0000000001-26-000001",
                    "0000000001-26-000002",
                    "0000000001-26-000003",
                ],
                "primaryDocument": [
                    "nvda-q1.htm",
                    "nvda-8k.htm",
                    "nvda-10k.htm",
                ],
            }
        },
    }

    adapter = SECResearchAdapter()

    with patch(
        "atlas.adapters.sec_research.requests.get"
    ) as mock_get:

        mock_get.return_value.json.return_value = response_data
        mock_get.return_value.raise_for_status.return_value = None

        results = adapter.get_company_filings(
            cik="0001045810",
        )

    assert len(results) == 3
    assert results[0]["source"] == "SEC"
    assert results[0]["form"] == "10-Q"
    assert results[0]["filing_date"] == "2026-08-01"


def test_sec_research_handles_request_failure():

    adapter = SECResearchAdapter()

    with patch(
        "atlas.adapters.sec_research.requests.get"
    ) as mock_get:

        mock_get.side_effect = Exception("network error")

        results = adapter.get_company_filings(
            cik="0001045810",
        )

    assert results == []


def test_sec_research_finds_cik_from_symbol():

    response_data = {
        "0": {
            "cik_str": 1045810,
            "ticker": "NVDA",
            "title": "NVIDIA CORP",
        }
    }

    adapter = SECResearchAdapter()

    with patch(
        "atlas.adapters.sec_research.requests.get"
    ) as mock_get:

        mock_get.return_value.json.return_value = response_data
        mock_get.return_value.raise_for_status.return_value = None

        cik = adapter.find_cik("NVDA")

    assert cik == "0001045810"


def test_sec_research_returns_none_for_unknown_symbol():

    response_data = {
        "0": {
            "cik_str": 1045810,
            "ticker": "NVDA",
            "title": "NVIDIA CORP",
        }
    }

    adapter = SECResearchAdapter()

    with patch(
        "atlas.adapters.sec_research.requests.get"
    ) as mock_get:

        mock_get.return_value.json.return_value = response_data
        mock_get.return_value.raise_for_status.return_value = None

        cik = adapter.find_cik("UNKNOWN")

    assert cik is None


def test_sec_research_prioritizes_relevant_filings():

    adapter = SECResearchAdapter()

    filings = [
        {
            "source": "SEC",
            "company": "NVIDIA CORP",
            "form": "4",
            "filing_date": "2026-08-12",
            "cik": "0001045810",
        },
        {
            "source": "SEC",
            "company": "NVIDIA CORP",
            "form": "10-Q",
            "filing_date": "2026-08-01",
            "cik": "0001045810",
        },
        {
            "source": "SEC",
            "company": "NVIDIA CORP",
            "form": "8-K",
            "filing_date": "2026-08-10",
            "cik": "0001045810",
        },
        {
            "source": "SEC",
            "company": "NVIDIA CORP",
            "form": "10-K",
            "filing_date": "2026-02-20",
            "cik": "0001045810",
        },
    ]

    ranked = adapter._prioritize_filings(filings)

    assert ranked[0]["form"] in {
        "10-Q",
        "8-K",
        "10-K",
    }

    assert len(ranked) <= 30


def test_sec_research_limits_filings():

    adapter = SECResearchAdapter()

    filings = [
        {
            "source": "SEC",
            "company": "NVIDIA CORP",
            "form": "4",
            "filing_date": f"2026-08-{(i % 12) + 1:02d}",
            "cik": "0001045810",
        }
        for i in range(100)
    ]

    ranked = adapter._prioritize_filings(filings)

    assert len(ranked) <= 30
