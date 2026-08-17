"""
SEC Research Adapter

Fetches recent SEC company filings for research.
"""

import requests


class SECResearchAdapter:
    """Fetches SEC filing information."""

    BASE_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

    HEADERS = {
        "User-Agent": "ATLAS Trading Research contact@example.com",
    }

    def find_cik(
        self,
        symbol: str,
    ) -> str | None:
        """Find a company's SEC CIK from its ticker symbol."""

        try:
            response = requests.get(
                "https://www.sec.gov/files/company_tickers.json",
                headers=self.HEADERS,
                timeout=10,
            )

            response.raise_for_status()
            data = response.json()

        except Exception:
            return None

        symbol_upper = symbol.upper()

        for item in data.values():
            ticker = str(
                item.get("ticker", "")
            ).upper()

            if ticker == symbol_upper:
                cik_str = item.get("cik_str")

                if cik_str is None:
                    return None

                return str(cik_str).zfill(10)

        return None

    @staticmethod
    def _prioritize_filings(
        filings: list[dict],
    ) -> list[dict]:
        """Prioritize relevant and recent SEC filings."""

        priority = {
            "10-K": 3,
            "10-Q": 3,
            "8-K": 3,
            "20-F": 3,
            "6-K": 3,
            "10-K/A": 2,
            "10-Q/A": 2,
            "8-K/A": 2,
            "13-F": 1,
            "4": 0,
        }

        def sort_key(filing: dict):
            form = filing.get("form", "")
            filing_date = filing.get(
                "filing_date",
                "",
            )

            return (
                priority.get(form, 0),
                filing_date,
            )

        ranked = sorted(
            filings,
            key=sort_key,
            reverse=True,
        )

        return ranked[:30]

    def get_company_filings(
        self,
        cik: str,
    ) -> list[dict]:
        """Return recent SEC company filings."""

        cik = str(cik).zfill(10)

        try:
            response = requests.get(
                self.BASE_URL.format(cik=cik),
                headers=self.HEADERS,
                timeout=10,
            )

            response.raise_for_status()
            data = response.json()

        except Exception:
            return []

        recent = (
            data.get("filings", {})
            .get("recent", {})
        )

        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get(
            "accessionNumber",
            [],
        )
        documents = recent.get(
            "primaryDocument",
            [],
        )

        results = []

        for index, form in enumerate(forms):

            filing_date = (
                dates[index]
                if index < len(dates)
                else ""
            )

            accession = (
                accessions[index]
                if index < len(accessions)
                else ""
            )

            document = (
                documents[index]
                if index < len(documents)
                else ""
            )

            results.append(
                {
                    "source": "SEC",
                    "company": data.get(
                        "name",
                        "",
                    ),
                    "form": form,
                    "filing_date": filing_date,
                    "accession_number": accession,
                    "primary_document": document,
                    "cik": cik,
                }
            )

        return self._prioritize_filings(results)
