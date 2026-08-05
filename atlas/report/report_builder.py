"""
ATLAS Report Builder
"""


class ReportBuilder:
    """Builds console reports."""

    def print_decision(self, decision):

        print()
        print("=" * 40)
        print("ATLAS INVESTMENT DECISION")
        print("=" * 40)
        print()

        print(f"Symbol      : {decision.symbol}")
        print(f"Decision    : {decision.action.value}")
        print(f"Evidence    : {decision.evidence:.1f}")
        print(f"Confidence  : {decision.confidence:.1f}")

        print()
        print("Analysts")

        for analyst in decision.analysts:
            print(f"✓ {analyst}")

        print()
        print("=" * 40)