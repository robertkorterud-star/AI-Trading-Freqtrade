#!/bin/bash

set -e

echo "🧠 ATLAS — forbedrer Decision Explanation..."

python - <<'PY'
from pathlib import Path

# ------------------------------------------------------------
# 1. Extend DecisionExplanation with an explicit decision path
# ------------------------------------------------------------

path = Path("atlas/models/decision_explanation.py")
text = path.read_text()

old = '''    adaptive_override: bool = False

    key_reasons: list[str] = field(
        default_factory=list
    )
'''

new = '''    adaptive_override: bool = False

    decision_path: list[str] = field(
        default_factory=list
    )

    key_reasons: list[str] = field(
        default_factory=list
    )
'''

if old not in text:
    raise SystemExit(
        "Could not find DecisionExplanation insertion point."
    )

path.write_text(text.replace(old, new))

# ------------------------------------------------------------
# 2. Build an explicit decision path
# ------------------------------------------------------------

path = Path("atlas/decision/explanation.py")
text = path.read_text()

old = '''    key_reasons = []

    if decision.dominant_action is not None:
'''

new = '''    decision_path = []

    if (
        decision.opposing_analysts
        and decision.dominant_action in {
            Action.BUY,
            Action.SELL,
        }
    ):
        decision_path.append(
            "Directional analyst signals are in conflict."
        )

    if decision.dominant_action is not None:
        decision_path.append(
            f"Dominant signal: "
            f"{decision.dominant_action.value} "
            f"with {decision.dominant_weight:.1f}% "
            f"weighted influence."
        )

    if decision.action == decision.dominant_action:
        decision_path.append(
            "Final decision follows the dominant signal."
        )
    elif decision.adaptive_override:
        decision_path.append(
            f"Adaptive weighting resolved the conflict "
            f"in favor of {decision.action.value}."
        )
    elif (
        decision.action == Action.HOLD
        and decision.dominant_action in {
            Action.BUY,
            Action.SELL,
        }
    ):
        decision_path.append(
            "ATLAS kept HOLD because the dominant "
            "directional signal did not clear the "
            "conflict-resolution gate."
        )
    else:
        decision_path.append(
            f"Final policy decision: {decision.action.value}."
        )

    decision_path.append(
        f"Decision margin: {decision.decision_margin:.1f}%."
    )

    decision_path.append(
        f"Robustness: {decision.robustness:.1f}% "
        f"({decision.robustness_level})."
    )

    key_reasons = []

    if decision.dominant_action is not None:
'''

if old not in text:
    raise SystemExit(
        "Could not find decision_path insertion point."
    )

text = text.replace(old, new)

old = '''        adaptive_override=decision.adaptive_override,
        key_reasons=key_reasons,
    )
'''

new = '''        adaptive_override=decision.adaptive_override,
        decision_path=decision_path,
        key_reasons=key_reasons,
    )
'''

if old not in text:
    raise SystemExit(
        "Could not find DecisionExplanation return block."
    )

path.write_text(text.replace(old, new))

# ------------------------------------------------------------
# 3. Add Decision Path to the dashboard
# ------------------------------------------------------------

path = Path("atlas/dashboard/templates/analysis.html")
text = path.read_text()

marker = '''            <div class="decision-reasoning">

                <h3>Why ATLAS decided this</h3>
'''

insert = '''            <div class="decision-path">

                <h3>Decision Path</h3>

                <div class="decision-path-list">

                    {% for step in dashboard.decision_explanation.decision_path %}

                        <div class="decision-path-step">

                            <span class="decision-path-number">
                                {{ loop.index }}
                            </span>

                            <span>
                                {{ step }}
                            </span>

                        </div>

                    {% endfor %}

                </div>

            </div>


            <div class="decision-reasoning">

                <h3>Why ATLAS decided this</h3>
'''

if marker not in text:
    raise SystemExit(
        "Could not find dashboard decision reasoning section."
    )

path.write_text(text.replace(marker, insert))

# ------------------------------------------------------------
# 4. Add lightweight styling
# ------------------------------------------------------------

path = Path("atlas/dashboard/templates/base.html")
text = path.read_text()

style_marker = "</style>"

css = '''
<style>
.decision-path {
    margin-top: 24px;
    padding-top: 20px;
    border-top: 1px solid #333;
}

.decision-path-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.decision-path-step {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 14px;
    border-radius: 8px;
    background: rgba(255,255,255,0.035);
}

.decision-path-number {
    min-width: 26px;
    height: 26px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: #222;
    font-weight: bold;
}
</style>
'''

if "decision-path-step" not in text:
    text = text.replace(style_marker, css + "\n" + style_marker)

path.write_text(text)

# ------------------------------------------------------------
# 5. Extend explanation tests
# ------------------------------------------------------------

path = Path("tests/test_decision_explanation.py")
text = path.read_text()

old = '''    assert explanation.adaptive_override is False
    assert explanation.key_reasons == []
'''

new = '''    assert explanation.adaptive_override is False
    assert explanation.decision_path == []
    assert explanation.key_reasons == []
'''

if old not in text:
    raise SystemExit(
        "Could not update explanation defaults test."
    )

text = text.replace(old, new)

text += '''

def test_explain_decision_builds_explicit_hold_conflict_path():
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.HOLD,
        confidence=77.7,
        evidence=78.3,
        analysts=[
            "Technical Analyst",
            "Company Analyst",
        ],
        dominant_action=Action.BUY,
        dominant_weight=66.7,
        opposing_analysts=[
            "Company Analyst",
        ],
        adaptive_override=False,
        decision_margin=33.3,
        robustness=46.8,
        robustness_level="WEAK",
    )

    explanation = explain_decision(
        decision,
        agreement=66.7,
    )

    assert explanation.action == Action.HOLD
    assert explanation.decision_path

    assert any(
        "conflict" in step.lower()
        for step in explanation.decision_path
    )

    assert any(
        "BUY" in step
        and "66.7%" in step
        for step in explanation.decision_path
    )

    assert any(
        "kept HOLD" in step
        and "conflict-resolution gate" in step
        for step in explanation.decision_path
    )

    assert any(
        "33.3%" in step
        for step in explanation.decision_path
    )

    assert any(
        "46.8%" in step
        and "WEAK" in step
        for step in explanation.decision_path
    )
'''

path.write_text(text)

print("✅ DecisionExplanation updated")
print("✅ Decision Path added to dashboard")
print("✅ CSS added")
print("✅ Tests added")
PY

echo
echo "🧪 Kjører målrettede tester..."
pytest -q tests/test_decision_explanation.py tests/test_dashboard_data_service.py

echo
echo "🧪 Kjører hele testpakken..."
pytest -q

echo
echo "🔍 Kontrollerer diff..."
git diff --check
git diff --stat

echo
echo "✅ Ferdig."
echo "Hvis alt er grønt:"
echo
echo "git add atlas/models/decision_explanation.py atlas/decision/explanation.py atlas/dashboard/templates/analysis.html atlas/dashboard/templates/base.html tests/test_decision_explanation.py"
echo 'git commit -m "ATLAS: explain decision path in dashboard"'
echo "git push origin feature/ask-atlas"
