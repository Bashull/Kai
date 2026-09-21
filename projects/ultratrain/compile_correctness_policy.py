from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CompileCorrectnessStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    NEEDS_CANARY = "NEEDS_CANARY"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class CompileCorrectnessResult:
    status: CompileCorrectnessStatus
    rules: tuple[str, ...] = field(default_factory=tuple)
    canaries: tuple[str, ...] = field(default_factory=tuple)
    decisions: tuple[str, ...] = field(default_factory=tuple)


def evaluate_compile_correctness(profile: dict[str, Any]) -> CompileCorrectnessResult:
    """Guard known torch.compile silent-correctness hazards by behavior, not version.

    PyTorch issue #197811 (opened 2026-09-20) demonstrates a nightly build silently
    reusing a Dynamo graph when closures capture different torch.Tensor method
    descriptors. Until upstream ships and we verify a fix, affected compositions
    require an eager-vs-compiled equivalence canary or must avoid descriptor-capturing
    closure factories in compiled regions.
    """
    if profile.get("torch_compile") is not True:
        return CompileCorrectnessResult(
            CompileCorrectnessStatus.SUPPORTED,
            decisions=("compile.disabled",),
        )

    if profile.get("captures_tensor_method_descriptor") is False:
        return CompileCorrectnessResult(
            CompileCorrectnessStatus.SUPPORTED,
            decisions=("compile.no_descriptor_closure_hazard",),
        )

    if profile.get("captures_tensor_method_descriptor") is None:
        return CompileCorrectnessResult(
            CompileCorrectnessStatus.NEEDS_CANARY,
            rules=("compile.dynamo.descriptor_closure_identity_guard",),
            canaries=("torch_compile_descriptor_closure_equivalence",),
        )

    if profile.get("descriptor_guard_fix_verified") is True:
        return CompileCorrectnessResult(
            CompileCorrectnessStatus.SUPPORTED,
            decisions=("compile.dynamo.descriptor_guard_fix_verified",),
        )

    if profile.get("eager_compiled_equivalence_passed") is True:
        return CompileCorrectnessResult(
            CompileCorrectnessStatus.SUPPORTED,
            decisions=("compile.descriptor_closure_equivalence_verified",),
        )

    return CompileCorrectnessResult(
        CompileCorrectnessStatus.NEEDS_CANARY,
        rules=("compile.dynamo.descriptor_closure_identity_guard",),
        canaries=("torch_compile_descriptor_closure_equivalence",),
    )
