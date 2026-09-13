from __future__ import annotations

from .hardware_doctor_contract import (
    CapabilityEvidence,
    CapabilityState,
    MemoryEstimate,
    ModelCapabilityProfile,
    PackageIdentity,
    RuntimeProviderDescriptor,
)


UNSLOTH_SNAPSHOT_SHA256 = "b3130f4e0d149fc65097b7a98dc80fdceaf3e1316b0dd2a4ad5fa4b36552c4e2"
QWEN38_SNAPSHOT_SHA256 = "2d7c7347977294a0cda25306f4654e1cb906c3b1f5848abf2e91dcf35d41394d"

_QWEN38_MLX_LFS_BYTES = {
    2: 9_351_192_422,
    4: 16_074_530_924,
    6: 22_797_869_090,
    8: 29_521_207_586,
}


def unsloth_2026_9_4_studio_runtime_descriptor() -> RuntimeProviderDescriptor:
    evidence = f"donor:unsloth-main.zip@sha256:{UNSLOTH_SNAPSHOT_SHA256}"
    return RuntimeProviderDescriptor(
        provider_id="unsloth-studio-2026.9.4",
        isolation="process",
        packages=(
            PackageIdentity("unsloth", "2026.9.4", source="donor-snapshot:package-version"),
            PackageIdentity("trl", "0.23.1", source="donor-snapshot:studio-requirements"),
            PackageIdentity("transformers", "5.5.0", source="donor-snapshot:studio-requirements"),
        ),
        capabilities=(
            CapabilityEvidence("model.qwen3_8", CapabilityState.DECLARED, evidence),
            CapabilityEvidence("export.gguf", CapabilityState.DECLARED, evidence),
            CapabilityEvidence("runtime.mlx", CapabilityState.DECLARED, evidence),
            CapabilityEvidence("runtime.stable_diffusion_cpp", CapabilityState.DECLARED, evidence),
        ),
        conflicts=(
            "canonical:trl>=1.13.0",
            "canonical:transformers>=5.16",
        ),
        license_boundary="core:Apache-2.0;studio-cli:AGPL-3.0",
    )


def qwen38_27b_uncensored_mlx_profile() -> ModelCapabilityProfile:
    evidence = f"donor:Qwen3.8-27B-Uncensored-MLX-main.zip@sha256:{QWEN38_SNAPSHOT_SHA256}"
    return ModelCapabilityProfile(
        model_id="Qwen3.8-27B-Uncensored-MLX",
        family="qwen3_5",
        baseline={
            "architecture": "Qwen3_5ForConditionalGeneration",
            "max_context": 262_144,
            "layers": 64,
            "attention_heads": 24,
            "kv_heads": 4,
        },
        deltas={
            "modalities": ["text", "image", "video"],
            "tool_calls": True,
            "thinking": True,
            "reasoning_effort": ["low", "medium", "xhigh"],
            "full_attention_interval": 4,
            "refusal_behavior_modified": True,
            "weights_embedded_in_archive": False,
        },
        evidence=(evidence,),
    )


def qwen38_mlx_memory_estimate(quant_bits: int) -> MemoryEstimate:
    if quant_bits not in _QWEN38_MLX_LFS_BYTES:
        raise ValueError(f"unsupported observed MLX quantization: {quant_bits!r}")
    assumptions = [
        "weights-only-lfs-payload",
        "kv-cache-not-included",
        "runtime-overhead-not-included",
        "vision-activation-memory-not-included",
    ]
    confidence = {2: 0.35, 4: 0.70, 6: 0.72, 8: 0.75}[quant_bits]
    if quant_bits == 2:
        assumptions.append("donor-card-severely-degraded")
    return MemoryEstimate(
        bytes_required=_QWEN38_MLX_LFS_BYTES[quant_bits],
        basis="estimated",
        confidence=confidence,
        assumptions=tuple(assumptions),
        evidence=f"donor-lfs-sum:sha256:{QWEN38_SNAPSHOT_SHA256}:mlx-{quant_bits}bit",
    )
