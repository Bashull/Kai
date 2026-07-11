from __future__ import annotations

from typing import Any

from .models import ActionPlan

READ_ONLY_ACTIONS = {
    "health", "roots", "list", "stat", "read_text", "search", "index",
    "duplicates_exact", "duplicates_images", "classify",
}
MUTATING_ACTIONS = {"mkdir", "copy", "move", "rename"}
ALLOWED_ACTIONS = READ_ONLY_ACTIONS | MUTATING_ACTIONS
PATH_FIELDS = {"path", "dest"}
AGENT_FIELDS = {
    "action", "path", "dest", "query", "recursive", "limit", "max_bytes",
    "dry_run", "confirm", "roots", "similarity",
}


class PolicyError(ValueError):
    pass


def _validate_path(value: Any, field: str) -> None:
    if value is None:
        return
    if not isinstance(value, str):
        raise PolicyError(f"{field} must be a string")
    if "\x00" in value:
        raise PolicyError(f"{field} contains a NUL byte")
    if not (value.startswith("/") or value.startswith("~/") or value == "~"):
        raise PolicyError(f"{field} must be absolute or home-relative")


def build_plan(request: dict[str, Any]) -> ActionPlan:
    action = str(request.get("action", "")).strip().lower()
    if action not in ALLOWED_ACTIONS:
        raise PolicyError(f"Action not allowed: {action or '<empty>'}")

    for field in PATH_FIELDS:
        _validate_path(request.get(field), field)

    if action in {"list", "stat", "read_text", "index", "classify", "mkdir"} and not request.get("path"):
        raise PolicyError(f"Action {action} requires path")
    if action in {"copy", "move", "rename"}:
        if not request.get("path"):
            raise PolicyError(f"Action {action} requires path")
        if not request.get("dest"):
            raise PolicyError(f"Action {action} requires dest")

    payload = {key: value for key, value in request.items() if key in AGENT_FIELDS}
    payload["action"] = action

    if action in MUTATING_ACTIONS:
        payload["dry_run"] = True
        payload["confirm"] = False
        return ActionPlan(
            action=action,
            risk="MUTATING_GUARDED",
            requires_confirmation=True,
            payload=payload,
        )

    payload["dry_run"] = False
    payload["confirm"] = False
    return ActionPlan(
        action=action,
        risk="READ_ONLY",
        requires_confirmation=False,
        payload=payload,
    )
