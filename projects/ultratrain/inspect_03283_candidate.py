"""Inspect AI 0.3.283 safety gates. STAGING only; never authorizes execution.
Sources: https://github.com/UKGovernmentBEIS/inspect_ai/releases/tag/0.3.283
https://github.com/UKGovernmentBEIS/inspect_ai/pull/5411
https://github.com/UKGovernmentBEIS/inspect_ai/pull/6006
"""
import re

def inspect_03283_findings(profile):
    if not isinstance(profile, dict):
        return [{"status": "NEEDS_CANARY", "rule": "inspect.03283.profile_shape"}]
    p = profile.get("packages", {})
    ev = profile.get("evaluation", {})
    ds = profile.get("inspect_dataset", {})
    rs = profile.get("inspect_resume", {})
    if not all(isinstance(x, dict) for x in (p, ev, ds, rs)):
        return [{"status": "NEEDS_CANARY", "rule": "inspect.03283.profile_shape"}]
    if ev.get("engine") != "inspect_ai" and not ds and not rs:
        return []
    versions = [p[k] for k in ("inspect_ai", "inspect-ai") if k in p]
    if "version" in ev:
        versions.append(ev["version"])
    parsed = []
    for raw in versions:
        m = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", raw) if isinstance(raw, str) else None
        parsed.append(tuple(map(int, m.groups())) if m else None)
    v = parsed[0] if parsed and None not in parsed and len(set(parsed)) == 1 else None
    out = []
    def add(status, rule):
        out.append({"status": status, "rule": rule})
    if v is None:
        add("NEEDS_CANARY", "inspect.03283.version_identity")
    fixed = v is not None and v >= (0, 3, 283)
    fields = ds.get("fields", [])
    if not isinstance(fields, list) or any(not isinstance(f, str) for f in fields):
        add("NEEDS_CANARY", "inspect.03283.dataset_fields_shape")
        fields = []
    if "checkpoint" in fields and ds.get("checkpoint_meaning") == "unrelated":
        if fixed and not ds.get("fieldspec_checkpoint_none") and not ds.get("fieldspec_checkpoint_alias"):
            add("UNSUPPORTED", "inspect.03283.reserved_checkpoint_collision")
        elif v is None:
            add("NEEDS_CANARY", "inspect.03283.reserved_checkpoint_version_unknown")
    if ds.get("sample_checkpoint_trigger_in_record"):
        add("UNSUPPORTED" if fixed else "NEEDS_CANARY", "inspect.03283.sample_trigger_forbidden")
    if ds.get("sample_checkpoint_overrides"):
        add("UNSUPPORTED" if v is not None and not fixed else "NEEDS_CANARY",
            "inspect.pre03283.sample_checkpoint_lost_on_reload" if v is not None and not fixed else "inspect.03283.checkpoint_roundtrip")
    if rs.get("mode") == "eval_set":
        if v is not None and not fixed and rs.get("log_trust") in ("shared", "untrusted"):
            add("UNSUPPORTED", "inspect.pre03283.eval_set_log_sandbox_injection")
        else:
            add("NEEDS_CANARY", "inspect.03283.eval_set_sandbox_resolution")
        if rs.get("resume_uses_log_sandbox"):
            add("UNSUPPORTED", "inspect.03283.eval_set_log_sandbox_authority_forbidden")
        if rs.get("mixed_sandbox_samples") and not rs.get("per_sample_sandbox_provenance"):
            add("UNSUPPORTED", "inspect.03283.mixed_sandbox_provenance_missing")
    if rs.get("mode") == "eval_retry" and rs.get("log_trust") in ("shared", "untrusted"):
        add("UNSUPPORTED", "inspect.03283.eval_retry_untrusted_log_sandbox")
    if rs.get("sandbox_config_ignored"):
        add("UNSUPPORTED", "inspect.03283.sandbox_config_not_applied")
    if rs.get("resume_after_cancellation"):
        add("NEEDS_CANARY", "inspect.03283.cancelled_span_persistence")
    return sorted(out, key=lambda f: (0 if f["status"] == "UNSUPPORTED" else 1, f["rule"]))
