"""Fail-closed guards for branches and filesystem mutation scope."""
from __future__ import annotations

import subprocess
from typing import AbstractSet, Sequence
from pathlib import Path

from .errors import LoopFactoryError
from .model import ErrorClass


DEFAULT_CANONICAL_BRANCHES = frozenset({"main", "master"})


def detect_git_branch(repo_root: Path) -> str:
    root = Path(repo_root).expanduser().resolve(strict=False)
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise LoopFactoryError(ErrorClass.ENV_MISSING, f"Cannot inspect git branch: {exc}") from exc

    branch = completed.stdout.strip()
    if completed.returncode != 0 or not branch or branch == "HEAD":
        detail = completed.stderr.strip() or "branch is missing or detached"
        raise LoopFactoryError(ErrorClass.ENV_MISSING, f"Cannot establish git branch: {detail}")
    return branch


def assert_noncanonical_branch(
    branch: str,
    canonical_branches: AbstractSet[str] = DEFAULT_CANONICAL_BRANCHES,
) -> None:
    normalized = branch.strip()
    if not normalized or normalized == "HEAD":
        raise LoopFactoryError(ErrorClass.ENV_MISSING, "Branch identity is missing or detached")
    if normalized in canonical_branches:
        raise LoopFactoryError(
            ErrorClass.CANONICAL_BRANCH_GUARD,
            f"Direct mutation on canonical branch '{normalized}' is forbidden",
        )


def assert_write_scope(target: Path, scopes: Sequence[Path]) -> None:
    resolved_target = Path(target).expanduser().resolve(strict=False)
    resolved_scopes = [Path(scope).expanduser().resolve(strict=False) for scope in scopes]
    if not resolved_scopes:
        raise LoopFactoryError(ErrorClass.WRITE_SCOPE_VIOLATION, "No write scope declared")

    for scope in resolved_scopes:
        if resolved_target == scope or scope in resolved_target.parents:
            return

    raise LoopFactoryError(
        ErrorClass.WRITE_SCOPE_VIOLATION,
        f"Target '{resolved_target}' is outside declared write scope",
    )
