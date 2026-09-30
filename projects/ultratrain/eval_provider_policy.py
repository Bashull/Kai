from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvalProviderDecision:
    allowed: bool
    rule: str
    needs_canary: bool = False


def evaluate_eval_provider(profile: dict) -> EvalProviderDecision:
    """Keep evaluation engines replaceable while protecting score comparability."""
    ev = profile.get("evaluation", {})
    provider = ev.get("provider")

    if provider == "lm_eval" and ev.get("custom_extension") and ev.get("forked_core"):
        return EvalProviderDecision(False, "eval.lm_eval.extensions_must_use_plugins")

    if provider == "lighteval" and ev.get("normalized_multichoice_probability"):
        if not ev.get("long_sequence_underflow_canary_passed"):
            return EvalProviderDecision(False, "eval.lighteval.long_mc_probability_canary", True)

    if provider == "inspect" and ev.get("view_exposed"):
        if not ev.get("scoped_authorization"):
            return EvalProviderDecision(False, "eval.inspect.view_requires_scoped_authorization")

    if ev.get("promotion_gate") and not ev.get("provider_version_pinned"):
        return EvalProviderDecision(False, "eval.provider.version_pin_required")

    return EvalProviderDecision(True, "eval.provider.supported")
