from __future__ import annotations

from audio_studio.providers.probes import ProbeTarget

VERIFIED_AT = "2026-08-27"

ACE_STEP_API_DOC = (
    "https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/API.md"
)
MINIMAX_MUSIC_API_DOC = (
    "https://platform.minimax.io/docs/api-reference/music-generation"
)
SUNO_PLATFORM = "https://platform.suno.com/"
ACE_STEP_ZEROGPU_SPACE = "https://huggingface.co/spaces/ACE-Step/Ace-Step-v1.5"
HF_ZEROGPU_DOC = "https://huggingface.co/docs/hub/spaces-zerogpu"


def ace_step_local_target(
    base_url: str = "http://127.0.0.1:8001",
) -> ProbeTarget:
    return ProbeTarget(
        provider_id="ace-step-1.5-local",
        capabilities=frozenset({
            "text_to_music", "cover", "repaint", "stems", "audio_understanding"
        }),
        runtime="LOCAL",
        cost_class="LOCAL",
        status_url=base_url.rstrip("/") + "/health",
        expected_json={
            "data": {"status": "ok", "service": "ACE-Step API"},
            "code": 200,
        },
        metadata={
            "contract_status": "OFFICIAL_VERIFIED",
            "contract_verified_at": VERIFIED_AT,
            "contract_source": ACE_STEP_API_DOC,
            "generation_endpoint": "/release_task",
            "models_endpoint": "/v1/models",
        },
    )


def ace_step_cloud_target() -> ProbeTarget:
    return ProbeTarget(
        provider_id="ace-step-1.5-cloud",
        capabilities=frozenset({"text_to_music", "cover", "repaint"}),
        runtime="REMOTE",
        cost_class="UNKNOWN",
        status_url="https://api.acemusic.ai/health",
        credential_pointer=(
            "termux:~/.agents/skills/acestep/scripts/config.json#api_key"
        ),
        expected_json={"text": "health check"},
        metadata={
            "contract_status": "LIVE_READ_ONLY_VERIFIED",
            "contract_verified_at": VERIFIED_AT,
            "client_script": "~/.agents/skills/acestep/scripts/acestep.sh",
            "api_mode": "completion",
            "generation_model_observed": "acemusic/acestep-v1.5-turbo",
        },
    )


def ace_step_zerogpu_target() -> ProbeTarget:
    return ProbeTarget(
        provider_id="ace-step-1.5-zerogpu",
        capabilities=frozenset({
            "text_to_music", "cover", "repaint", "quality_scoring", "lrc"
        }),
        runtime="REMOTE",
        cost_class="FREE",
        status_url="https://ace-step-ace-step-v1-5.hf.space/config",
        expected_json={
            "version": "6.2.0",
            "api_prefix": "/gradio_api",
            "root": "https://ace-step-ace-step-v1-5.hf.space",
        },
        metadata={
            "contract_status": "OFFICIAL_FREE_LIMITED_LIVE_VERIFIED",
            "contract_verified_at": VERIFIED_AT,
            "contract_source": ACE_STEP_ZEROGPU_SPACE,
            "cost_source": HF_ZEROGPU_DOC,
            "quota_class": "DAILY_ZEROGPU_QUOTA",
            "generation_endpoint": "/generation_wrapper",
            "generation_transport": "GRADIO_API",
            "generation_auth": "HF_SESSION_AT_EXECUTION",
            "config_contract_size_observed": 386161,
            "api_info_contract_size_observed": 309330,
        },
    )


def minimax_music_api_target() -> ProbeTarget:
    return ProbeTarget(
        provider_id="minimax-music-3-api",
        capabilities=frozenset({"text_to_music", "cover"}),
        runtime="REMOTE",
        cost_class="PAID",
        policy_blocker=(
            "LEGACY_PAID_USERS_ONLY_AFTER_2026-08-20;"
            "FREE_MUSIC_APIS_DISCONTINUED"
        ),
        metadata={
            "contract_status": "OFFICIAL_VERIFIED_LEGACY",
            "contract_verified_at": VERIFIED_AT,
            "contract_source": MINIMAX_MUSIC_API_DOC,
            "generation_endpoint": "https://api.minimax.io/v1/music_generation",
        },
    )


def suno_platform_target() -> ProbeTarget:
    return ProbeTarget(
        provider_id="suno-platform",
        capabilities=frozenset({"text_to_music", "cover", "mashup"}),
        runtime="REMOTE",
        cost_class="UNKNOWN",
        metadata={
            "contract_status": "PLATFORM_CONFIRMED_DOCS_AUTH_REQUIRED",
            "contract_verified_at": VERIFIED_AT,
            "contract_source": SUNO_PLATFORM,
        },
    )
