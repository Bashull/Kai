from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .hardware_doctor_contract import PlannerCapabilityInput
from .planner_capability_adapter import adapt_training_request


PlannerCallable = Callable[[dict[str, Any]], Any]


def plan_training_with_capabilities(
    request: dict[str, Any],
    capability_input: PlannerCapabilityInput,
    *,
    planner: PlannerCallable | None = None,
) -> Any:
    """Adapt evidence into a copy of the request, then delegate to Smart Planner."""
    if planner is None:
        from .smart_planner import plan_training

        planner = plan_training
    return planner(adapt_training_request(request, capability_input))
