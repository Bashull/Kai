"""UltraTrain release gates: Hub 2.3.0 and SGLang CVE-2026-112266.
STAGING only: claims, not runtime attestation. No network/file/GPU side effects.
Sources: https://github.com/huggingface/huggingface_hub/releases/tag/v2.3.0
         https://github.com/advisories/GHSA-8v54-r9x8-p94v
"""
from __future__ import annotations
import re
from typing import Any

_V = re.compile(r"^v?(\d+)\.(\d+)(?:\.(\d+))?$", re.ASCII)
_PRIORITY = {"UNSUPPORTED": 2, "NEEDS_CANARY": 1}

def _version(raw: Any) -> tuple[int, int, int] | None:
    if not isinstance(raw, str):
        return None
    m = _V.fullmatch(raw.strip())
    return (int(m[1]), int(m[2]), int(m[3] or 0)) if m else None

def findings_release_20261024(profile: dict[str, Any]) -> list[dict[str, str]]:
    if not isinstance(profile, dict) or any(not isinstance(profile.get(k, {}), dict)
                                            for k in ("packages", "hub", "runtime")):
        return [{"status": "NEEDS_CANARY", "rule": "release.1024.profile_shape", "canary": "profile_schema"}]
    pkg, hub, runtime = profile.get("packages", {}), profile.get("hub", {}), profile.get("runtime", {})
    out: list[dict[str, str]] = []
    def add(status: str, rule: str, canary: str = "") -> None:
        out.append({"status": status, "rule": rule, "canary": canary})

    active = any(hub.get(k) for k in ("create_commit", "destructive_commit", "delete_and_readd",
                                     "recursive_listing", "live_follow",
                                     "sharded_safetensors_bulk_metadata", "hf_jobs_run"))
    if active:
        ids = [pkg[k] for k in ("huggingface_hub", "huggingface-hub") if k in pkg]
        if "version" in hub:
            ids.append(hub["version"])
        parsed = [_version(v) for v in ids]
        if not parsed or any(v is None for v in parsed) or len(set(parsed)) != 1:
            add("NEEDS_CANARY", "hub.230.version_identity", "lockfile_runtime_package_identity")
            hv = None
        else:
            hv = parsed[0]
        destructive = bool(hub.get("destructive_commit") or hub.get("delete_and_readd"))
        if hub.get("delete_and_readd") and hub.get("readd_unchanged_files"):
            if hv is not None and hv < (2, 3, 0):
                add("UNSUPPORTED", "hub.pre230.delete_readd_silent_loss", "same_commit_readd_preservation")
            else:
                add("NEEDS_CANARY", "hub.230.delete_readd_integrity", "same_commit_readd_preservation")
        if destructive:
            if hub.get("post_commit_manifest_verified") is not True:
                add("NEEDS_CANARY", "hub.230.post_commit_manifest_required", "remote_tree_diff_and_hash_receipts")
            if hub.get("rollback_snapshot_available") is not True:
                add("NEEDS_CANARY", "hub.230.rollback_snapshot_required", "restore_snapshot_and_manifest")
        if hub.get("live_follow"):
            if hub.get("target_kind") != "bucket":
                add("UNSUPPORTED", "hub.230.live_follow_buckets_only", "disable_repo_live_follow")
            elif hv is not None and hv < (2, 3, 0):
                add("UNSUPPORTED", "hub.pre230.live_follow_unavailable")
            else:
                n = hub.get("max_followed_buckets")
                if not isinstance(n, int) or isinstance(n, bool) or n < 1:
                    add("NEEDS_CANARY", "hub.230.live_follow_connection_budget", "bucket_subscription_limit_and_close")
                else:
                    add("NEEDS_CANARY", "hub.230.bucket_cache_freshness", "external_writer_event_reconnect_and_cleanup")
        if hub.get("recursive_listing"):
            if hv is not None and hv < (2, 3, 0):
                add("NEEDS_CANARY", "hub.pre230.large_repo_listing_latency", "bounded_listing_benchmark")
            else:
                workers = hub.get("max_workers", 16)
                if not isinstance(workers, int) or isinstance(workers, bool) or not 1 <= workers <= 64:
                    add("UNSUPPORTED", "hub.230.listing_workers_invalid", "set_concurrency_budget")
                else:
                    add("NEEDS_CANARY", "hub.230.parallel_listing_parity", "recursive_path_set_maxdepth_and_rate_limit")
        if hub.get("sharded_safetensors_bulk_metadata"):
            if hv is not None and hv < (2, 3, 0):
                add("UNSUPPORTED", "hub.pre230.bulk_shard_metadata_unavailable")
            elif hub.get("revision") not in (None, "main"):
                add("UNSUPPORTED", "hub.230.bulk_shard_metadata_main_only", "pinned_revision_fallback")
            else:
                add("NEEDS_CANARY", "hub.230.bulk_shard_metadata_parity", "shard_headers_revision_and_hash")
        if hub.get("hf_jobs_run") and hub.get("trust_cli_log_end_as_completion"):
            add("UNSUPPORTED", "hub.230.job_logs_not_completion_proof", "job_terminal_state_and_metrics_receipt")

    if runtime.get("sglang") or runtime.get("provider") == "sglang":
        sv = _version(pkg.get("sglang") or runtime.get("sglang_version"))
        if sv is None:
            add("NEEDS_CANARY", "sglang.112266.version_identity", "sglang_lockfile_runtime_probe")
        exposed = runtime.get("network_exposure") in {"public", "lan", "untrusted"}
        multi = runtime.get("multi_tenant") is True
        untrusted = runtime.get("untrusted_api_clients") is True
        forwarded = runtime.get("client_rid_forwarded") is True
        authorized = runtime.get("tenant_scoped_cancel_authorized") is True
        if (multi or untrusted) and forwarded and not authorized:
            add("UNSUPPORTED", "sglang.112266.cross_tenant_rid_abort", "tenant_isolation_abort_ownership")
        if exposed and (multi or untrusted):
            if sv is not None and sv <= (0, 5, 22):
                add("UNSUPPORTED", "sglang.112266.exposed_affected_version", "reverse_proxy_rid_normalization_and_auth")
            else:
                add("NEEDS_CANARY", "sglang.112266.fix_unverified", "patched_code_and_cross_tenant_abort_regression")
        if multi and not authorized:
            add("NEEDS_CANARY", "sglang.112266.cancel_ownership_unverified", "tenant_scoped_abort_authorization")
        if runtime.get("assume_version_alone_proves_rid_isolation"):
            add("UNSUPPORTED", "sglang.112266.version_not_sufficient_for_isolation")
    return sorted(out, key=lambda x: (-_PRIORITY[x["status"]], x["rule"]))
