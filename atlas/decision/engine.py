"""
Decision Engine
"""

from collections.abc import Iterable

from atlas.decision.aggregator import EvidenceAggregator
from atlas.decision.intelligence_layer import IntelligenceLayer
from atlas.decision.policy import determine_action
from atlas.intelligence.signal_ensemble import SignalEnsemble, SignalInput
from atlas.models.analysis_result import AnalysisResult
from atlas.models.action import Action
from atlas.trading.agent_weight_engine import AgentWeightEngine
from atlas.models.decision_result import DecisionResult
from atlas.trading.expected_return_service import ExpectedReturnService
from atlas.trading.trading_cost_model import TradingCostModel
from atlas.risk.manager import RiskManager, RiskAssessment
from atlas.portfolio.manager import PortfolioManager, PortfolioAssessment, PortfolioPosition


class DecisionEngine:
    """Creates the final investment decision."""

    def __init__(
        self,
        expected_return_service=None,
        risk_manager=None,
        portfolio_manager=None,
        position_exit_engine=None,
        trading_cost_model=None,
    ):
        self.aggregator = EvidenceAggregator()
        self.intelligence = IntelligenceLayer()
        self.signal_ensemble = SignalEnsemble()
        self.agent_weight_engine = None
        self.expected_return_service = expected_return_service
        self.risk_manager = risk_manager
        self.portfolio_manager = portfolio_manager
        self.position_exit_engine = position_exit_engine
        self.trading_cost_model = trading_cost_model
        self.last_intelligence = None
        self.last_ensemble_signal = None
        self.last_risk_assessment = None
        self.last_portfolio_assessment = None

    def _strongest_action_support(self, action: Action):
        """Return strongest learned support for an action."""
        if self.agent_weight_engine is None:
            return None

        try:
            weights = self.agent_weight_engine.calculate(action=action.value)
        except TypeError:
            weights = self.agent_weight_engine.calculate()

        if not weights:
            return None

        analyst, weight = max(weights.items(), key=lambda item: item[1])

        return {
            "analyst": analyst,
            "weight": weight,
            "action": action.value,
        }

    def _strongest_learned_action_support(self):
        """Return the strongest learned directional support."""
        if self.agent_weight_engine is None:
            return None

        supports = []

        for action in (Action.BUY, Action.SELL):
            support = self._strongest_action_support(action)
            if support is not None:
                supports.append(support)

        if not supports:
            return None

        return max(supports, key=lambda item: item["weight"])

    def evaluate_algorithm_signals(
        self,
        signals: Iterable,
        *,
        fusion_result=None,
        price: float | None = None,
        equity: float | None = None,
        current_exposure_pct: float = 0.0,
        drawdown_pct: float = 0.0,
        portfolio_positions: Iterable[PortfolioPosition] = (),
        current_position: float = 0.0,
        last_buy_price: float | None = None,
        average_price: float | None = None,
        peak_price: float | None = None,
    ) -> DecisionResult:
        """Evaluate algorithm signals through the canonical DecisionEngine.

        Algorithm signals remain owned by the algorithm layer. This method
        is the explicit adapter boundary that lets Signal Fusion and raw
        algorithm output enter the canonical analyst/evidence contract
        without making the algorithm package a second decision owner.
        """
        algorithm_signals = tuple(signals)
        if not algorithm_signals and fusion_result is None:
            raise ValueError("No algorithm signals provided.")

        converted = [self._algorithm_signal_to_analysis(signal) for signal in algorithm_signals]

        if fusion_result is not None:
            converted.append(self._fusion_result_to_analysis(fusion_result))

        return self.evaluate(
            converted,
            price=price,
            equity=equity,
            current_exposure_pct=current_exposure_pct,
            drawdown_pct=drawdown_pct,
            portfolio_positions=portfolio_positions,
            current_position=current_position,
            last_buy_price=last_buy_price,
            average_price=average_price,
            peak_price=peak_price,
        )

    @staticmethod
    def _algorithm_signal_to_analysis(signal) -> AnalysisResult:
        """Adapt one AlgorithmSignal to the canonical analysis contract."""
        score = float(getattr(signal, "score", 50.0))
        evidence = max(0.0, min(100.0, abs(score - 50.0) * 2.0))
        confidence = DecisionEngine._normalize_algorithm_confidence(
            float(getattr(signal, "confidence", 0.0))
        )

        return AnalysisResult(
            analyst=f"algorithm:{getattr(signal, 'algorithm', 'unknown')}",
            symbol=signal.symbol,
            action=Action(signal.action),
            confidence=confidence,
            evidence=evidence,
            reasoning=list(getattr(signal, "reasoning", [])),
            signal_confidence=confidence,
            metadata={
                "algorithm": getattr(signal, "algorithm", "unknown"),
                "timeframe": getattr(signal, "timeframe", ""),
                "score": score,
                "expected_edge": getattr(signal, "expected_edge", None),
            },
        )

    @staticmethod
    def _fusion_result_to_analysis(fusion_result) -> AnalysisResult:
        """Adapt Signal Fusion output to the canonical analysis contract."""
        return AnalysisResult(
            analyst="signal_fusion",
            symbol=fusion_result.symbol,
            action=Action(fusion_result.action),
            confidence=float(fusion_result.confidence),
            evidence=max(
                0.0,
                min(100.0, abs(float(fusion_result.score) - 50.0) * 2.0),
            ),
            reasoning=list(fusion_result.reasoning),
            signal_confidence=float(fusion_result.confidence),
        )

    @staticmethod
    def _normalize_algorithm_confidence(value: float) -> float:
        """Normalize algorithm confidence to the 0-100 DecisionEngine contract."""
        if value < 0.0:
            return 0.0
        if value <= 1.0:
            return value * 100.0
        return min(100.0, value)

    def evaluate(
        self,
        results: list[AnalysisResult],
        *,
        price: float | None = None,
        equity: float | None = None,
        current_exposure_pct: float = 0.0,
        drawdown_pct: float = 0.0,
        portfolio_positions: Iterable[PortfolioPosition] = (),
        current_position: float = 0.0,
        last_buy_price: float | None = None,
        average_price: float | None = None,
        peak_price: float | None = None,
    ) -> DecisionResult:
        if not results:
            raise ValueError("No analysis results provided.")

        weights = None
        if self.agent_weight_engine is not None:
            weights = self.agent_weight_engine.calculate()

        ensemble_inputs = [
            SignalInput(
                name=result.analyst,
                action=result.action,
                confidence=(
                    result.signal_confidence
                    if result.signal_confidence is not None
                    else result.confidence
                ),
                reasons=tuple(result.reasoning),
            )
            for result in results
        ]
        ensemble_signal = self.signal_ensemble.combine(ensemble_inputs)
        self.last_ensemble_signal = ensemble_signal

        summary = self.aggregator.summarize(results, weights=weights)
        intelligence = self.intelligence.summarize(results, weights=weights)
        self.last_intelligence = intelligence

        weighted_signals = {
            Action.BUY: intelligence.weighted_buy,
            Action.HOLD: intelligence.weighted_hold,
            Action.SELL: intelligence.weighted_sell,
        }

        ranked_signals = sorted(
            weighted_signals.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        dominant_action = ranked_signals[0][0]
        dominant_weight = ranked_signals[0][1]
        action_support = self._strongest_learned_action_support()
        second_weight = ranked_signals[1][1] if len(ranked_signals) > 1 else 0.0
        decision_margin = dominant_weight - second_weight

        opposing_analysts = [
            result.analyst
            for result in results
            if result.action != dominant_action
        ]

        unanimous = (
            intelligence.buy_count == len(results)
            or intelligence.hold_count == len(results)
            or intelligence.sell_count == len(results)
        )

        policy_action = determine_action(
            evidence=summary["evidence"],
            agreement=intelligence.agreement,
            conflict=intelligence.conflict,
            buy_count=intelligence.buy_count,
            hold_count=intelligence.hold_count,
            sell_count=intelligence.sell_count,
        )

        action = policy_action
        adaptive_override = False

        if unanimous:
            action = dominant_action
        elif (
            weights
            and intelligence.weighted_conflict
            and dominant_action in {Action.BUY, Action.SELL}
            and dominant_weight >= 60.0
            and decision_margin >= 20.0
            and summary["evidence"] >= 80.0
        ):
            action = dominant_action
            adaptive_override = True

        if action in {Action.BUY, Action.HOLD, Action.SELL} and self.position_exit_engine is not None:
            from atlas.algorithms.position_exit import PositionContext, PositionAction

            position_decision = self.position_exit_engine.decide(
                action,
                PositionContext(
                    current_position=current_position,
                    entry_price=last_buy_price,
                    current_price=price,
                    peak_price=(
                        peak_price
                        if peak_price is not None
                        else average_price
                    ),
                    confidence=summary["confidence"] / 100.0,
                    risk_score=0.0,
                ),
            )
            if position_decision.action is PositionAction.EXIT:
                action = Action.SELL
            elif position_decision.action is PositionAction.REDUCE:
                action = Action.SELL
                current_position = max(
                    0.0,
                    current_position - position_decision.target_position,
                )
            elif position_decision.action is PositionAction.HOLD:
                action = Action.HOLD

        expected_return = 0.0
        expected_return_ready = False
        if self.expected_return_service is not None:
            estimate_with_status = getattr(
                self.expected_return_service,
                "estimate_with_status",
                None,
            )
            if estimate_with_status is not None:
                estimate = estimate_with_status(
                    symbol=results[0].symbol,
                    action=action,
                )
                expected_return = estimate.value
                expected_return_ready = estimate.ready
            else:
                expected_return = self.expected_return_service.estimate(
                    symbol=results[0].symbol,
                    action=action,
                )

        economic_gate_blocked = False
        if (
            action is Action.BUY
            and expected_return_ready
            and self.trading_cost_model is not None
            and self.trading_cost_model.net_return(expected_return) <= 0.0
        ):
            action = Action.HOLD
            economic_gate_blocked = True

        risk_assessment: RiskAssessment | None = None
        if self.risk_manager is not None:
            if price is None or equity is None:
                raise ValueError(
                    "price and equity are required when risk_manager is configured"
                )
            risk_assessment = self.risk_manager.assess(
                action=action,
                price=price,
                equity=equity,
                current_exposure_pct=current_exposure_pct,
                drawdown_pct=drawdown_pct,
                current_position=current_position,
            )
            self.last_risk_assessment = risk_assessment
            if not risk_assessment.allowed and action in {Action.BUY, Action.SELL}:
                action = Action.HOLD

        portfolio_assessment: PortfolioAssessment | None = None
        if self.portfolio_manager is not None and action is Action.BUY:
            if equity is None:
                raise ValueError(
                    "equity is required when portfolio_manager is configured"
                )

            requested_value = (
                risk_assessment.position_value
                if risk_assessment is not None
                else 0.0
            )
            portfolio_assessment = self.portfolio_manager.assess(
                symbol=results[0].symbol,
                requested_value=requested_value,
                equity=equity,
                positions=portfolio_positions,
            )
            self.last_portfolio_assessment = portfolio_assessment
            if not portfolio_assessment.allowed:
                action = Action.HOLD

        raw_robustness = decision_margin * 0.7 + summary["evidence"] * 0.3
        robustness = min(100.0, raw_robustness, summary["evidence"])

        if summary["evidence"] < 60.0:
            robustness_level = "WEAK"
        elif summary["evidence"] < 80.0:
            robustness_level = "MODERATE" if robustness >= 60.0 else "WEAK"
        elif robustness >= 80.0:
            robustness_level = "STRONG"
        elif robustness >= 60.0:
            robustness_level = "MODERATE"
        else:
            robustness_level = "WEAK"

        reasoning = [
            "Decision based on combined analyst evidence.",
            f"Overall evidence: {summary['evidence']:.1f}/100.",
            f"Overall confidence: {summary['confidence']:.1f}/100.",
            f"Analyst agreement: {intelligence.agreement:.1f}%.",
            f"Signal ensemble: {ensemble_signal.action.value} with "
            f"{ensemble_signal.confidence:.1f}% signal confidence.",
            f"Dominant signal: {dominant_action.value} with "
            f"{dominant_weight:.1f}% weighted influence.",
        ]

        if opposing_analysts:
            reasoning.append("Opposing analysts: " + ", ".join(opposing_analysts) + ".")

        if weights:
            reasoning.append(
                f"Adaptive weighting: {dominant_action.value} has "
                f"{dominant_weight:.1f}% weighted influence."
            )

        if action_support:
            reasoning.append(
                f"Learned support: {action_support['analyst']} supports "
                f"{action_support['action']} with "
                f"{action_support['weight'] * 100:.1f}% learned weight."
            )

        if adaptive_override:
            reasoning.append(
                "Adaptive weighting allowed the dominant signal to overcome "
                "the opposing analyst signals."
            )

        if intelligence.conflict and not adaptive_override:
            reasoning.append("Decision held because analyst signals conflict.")

        for analyst in summary.get("analyst_breakdown", []):
            reasoning.append(
                f"{analyst['analyst']}: {analyst['action']} "
                f"(evidence {analyst['evidence']:.1f}, "
                f"confidence {analyst['confidence']:.1f})."
            )
            for detail in analyst.get("reasoning", []):
                reasoning.append(f"  {detail}")

        reasoning.append(
            f"Decision robustness: {robustness:.1f}% ({robustness_level})."
        )

        if risk_assessment is not None:
            reasoning.append(
                f"Risk assessment: {risk_assessment.risk_level} "
                f"({'allowed' if risk_assessment.allowed else 'blocked'})."
            )
            reasoning.extend(f"Risk: {reason}" for reason in risk_assessment.reasons)
            if not risk_assessment.allowed and action is Action.HOLD:
                reasoning.append(
                    "Risk management blocked the directional decision; final action is HOLD."
                )

        if portfolio_assessment is not None:
            reasoning.append(
                "Portfolio assessment: "
                f"{'allowed' if portfolio_assessment.allowed else 'blocked'} "
                f"({portfolio_assessment.approved_value:.2f} allocation)."
            )
            reasoning.extend(
                f"Portfolio: {reason}" for reason in portfolio_assessment.reasons
            )
            if not portfolio_assessment.allowed and action is Action.HOLD:
                reasoning.append(
                    "Portfolio management blocked the allocation; final action is HOLD."
                )

        if self.expected_return_service is not None:
            reasoning.append(
                f"Expected gross return: {expected_return * 100:.2f}%."
            )

        if economic_gate_blocked:
            reasoning.append(
                "Economic gate blocked BUY because expected net return "
                "after trading costs is not positive; final action is HOLD."
            )

        return DecisionResult(
            symbol=results[0].symbol,
            action=action,
            confidence=summary["confidence"],
            evidence=summary["evidence"],
            analysts=[r.analyst for r in results],
            agent_weights=weights or {},
            dominant_action=dominant_action,
            dominant_weight=dominant_weight,
            action_support_analyst=action_support["analyst"] if action_support else None,
            action_support_action=Action(action_support["action"]) if action_support else None,
            action_support_weight=action_support["weight"] if action_support else 0.0,
            opposing_analysts=opposing_analysts,
            adaptive_override=adaptive_override,
            decision_margin=decision_margin,
            robustness=robustness,
            robustness_level=robustness_level,
            reasoning=reasoning,
            expected_return=expected_return,
            expected_return_ready=expected_return_ready,
            ensemble_action=ensemble_signal.action,
            ensemble_confidence=ensemble_signal.confidence,
            risk_assessment=risk_assessment,
            portfolio_assessment=portfolio_assessment,
        )
