from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable

from audio_studio.execution import AuthorizationReceipt, ExecutionBlocked

SPACE_ID = "ACE-Step/Ace-Step-v1.5"
RUNTIME_ROOT = "https://ace-step-ace-step-v1-5.hf.space"
API_NAME = "/generation_wrapper"
CONTRACT_INPUT_COUNT = 49


@dataclass(frozen=True)
class ZeroGpuCanaryRequest:
    prompt: str
    duration_seconds: int = 10
    batch_size: int = 1
    vocal_language: str = "unknown"
    seed: str = "-1"


@dataclass(frozen=True)
class GradioCall:
    space_id: str
    runtime_root: str
    api_name: str
    contract_input_count: int
    kwargs: dict[str, Any]
    max_attempts: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compile_zerogpu_canary(
    request: ZeroGpuCanaryRequest,
    receipt: AuthorizationReceipt,
) -> GradioCall:
    """Compile the single free canary. This function never performs I/O."""
    if not receipt.allowed:
        raise ExecutionBlocked(receipt.reason)
    if receipt.provider_id != "ace-step-1.5-zerogpu":
        raise ExecutionBlocked("WRONG_PROVIDER_RECEIPT")
    if receipt.cost_class.upper() != "FREE":
        raise ExecutionBlocked("FREE_ROUTE_REQUIRED")
    prompt = request.prompt.strip()
    if not prompt:
        raise ValueError("prompt is required")
    if request.duration_seconds != 10:
        raise ValueError("canary duration must be exactly 10 seconds")
    if request.batch_size != 1:
        raise ValueError("canary batch size must be exactly 1")

    return GradioCall(
        SPACE_ID,
        RUNTIME_ROOT,
        API_NAME,
        CONTRACT_INPUT_COUNT,
        {
            "selected_model": "acestep-v15-turbo",
            "generation_mode": "simple",
            "simple_query_input": prompt,
            "simple_vocal_language": request.vocal_language,
            "param_4": "",
            "param_5": "",
            "param_10": 8,
            "param_12": True,
            "param_13": request.seed,
            "param_14": None,
            "param_15": request.duration_seconds,
            "param_16": request.batch_size,
            "param_17": None,
            "param_18": "",
            "param_30": "mp3",
            "param_43": False,
            "param_44": False,
            "param_47": None,
        },
    )


def execute_zerogpu_canary(
    call: GradioCall,
    submitter: Callable[[GradioCall], Any],
) -> Any:
    """Execute exactly once through an injected transport; no retry loop exists."""
    if call.max_attempts != 1:
        raise ExecutionBlocked("AUTOMATIC_RETRIES_FORBIDDEN")
    return submitter(call)


def submit_with_gradio_client(
    call: GradioCall,
    *,
    token: str,
    download_files: str,
    client_factory: Callable[..., Any] | None = None,
) -> Any:
    """Submit one call using a caller-supplied HF token; the token is never serialized."""
    if call.max_attempts != 1:
        raise ExecutionBlocked("AUTOMATIC_RETRIES_FORBIDDEN")
    if not token:
        raise ExecutionBlocked("HF_AUTH_REQUIRED")
    if client_factory is None:
        from gradio_client import Client
        client_factory = Client
    client = client_factory(
        call.space_id,
        token=token,
        verbose=False,
        download_files=download_files,
    )
    return client.predict(api_name=call.api_name, **call.kwargs)
