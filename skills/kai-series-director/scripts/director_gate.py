#!/usr/bin/env python3
"""Non-executing, deterministic KAI Series Director plan gate.

No video decoding, remote requests, model inference, playback, engine execution,
production authorization, payments or rights clearance are performed here.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SCHEMA = "kai.director.plan/0.4-candidate"
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
VALID_MODES = {"film", "game", "hybrid"}
VALID_GEARS = {"G1", "G2", "G3"}
KNOWN_JOBS = {"DRAFT", "PREFLIGHT", "NOT_SUBMITTED", "SUBMITTED", "RUNNING",
              "COMPLETED", "FAILED", "CANCELLED", "SUBMIT_UNKNOWN"}


def _sha256(value: object) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _list(obj: dict, key: str, errors: list[str]) -> list:
    value = obj.get(key, [])
    if not isinstance(value, list):
        errors.append(f"{key} must be an array")
        return []
    return value


def evaluate_plan(plan: dict) -> dict:
    """Validate planning contracts, output conservative, machine-readable gates.

    Returned `media_decode`, `visual_review`, `acceptance` ALWAYS NOT_RUN because
    this module has no decoder, trusted reviewer or runtime/engine verifier.
    """
    errors: list[str] = []
    blockers: list[str] = []
    warnings: list[str] = []
    jobs: list[dict] = []
    repairs: list[dict] = []
    output = {
        "schema_version": SCHEMA,
        "project_id": plan.get("project_id") if isinstance(plan, dict) else None,
        "status": "BLOCKED", "delivery_status": "RIGHTS_PENDING",
        "generation_authorized": False,
        "media_decode": "NOT_RUN", "visual_review": "NOT_RUN",
        "audio_review": "NOT_RUN", "engine_execution": "NOT_RUN",
        "acceptance": "NOT_RUN", "gameplay_status": "NOT_APPLICABLE",
        "provider_actions": jobs, "repair_actions": repairs,
        "errors": errors, "blockers": blockers, "warnings": warnings,
        "authority": "KAI_MEDIA_FORGE_OMEGA_EXTERNAL",
        "evidence_scope": "CONTRACT_STATIC_ONLY",
    }
    if not isinstance(plan, dict):
        errors.append("plan must be JSON object")
        return output
    if plan.get("schema_version") != SCHEMA:
        errors.append(f"schema_version must be {SCHEMA}")
    if not isinstance(plan.get("project_id"), str) or not plan["project_id"].strip():
        errors.append("project_id is required")
    if plan.get("mode") not in VALID_MODES:
        errors.append("mode must be film/game/hybrid")
    if plan.get("gear") not in VALID_GEARS:
        errors.append("gear must be G1/G2/G3")

    assets = _list(plan, "assets", errors)
    shots = _list(plan, "shots", errors)
    gameplay = _list(plan, "gameplay", errors)
    provider_jobs = _list(plan, "provider_jobs", errors)
    repair_cycles = _list(plan, "repair_cycles", errors)
    asset_by_id: dict[str, dict] = {}
    rights_ok = True
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict) or not asset.get("id"):
            errors.append(f"assets[{index}] requires id")
            continue
        aid = str(asset["id"])
        if aid in asset_by_id:
            errors.append(f"duplicate asset id: {aid}")
        asset_by_id[aid] = asset
        if not asset.get("state_version") or not asset.get("canon_ref"):
            errors.append(f"asset {aid}: canon_ref and state_version required")
        if not asset.get("rights_evidence") or asset.get("license") in {None, "", "UNKNOWN"}:
            rights_ok = False
            blockers.append(f"asset {aid}: rights provenance or license missing")

    shot_ids: set[str] = set()
    for index, shot in enumerate(shots):
        if not isinstance(shot, dict):
            errors.append(f"shots[{index}] must be an object")
            continue
        sid = str(shot.get("id", ""))
        if not sid:
            errors.append(f"shots[{index}] id required")
        if sid in shot_ids:
            errors.append(f"duplicate shot id {sid}")
        shot_ids.add(sid)
        if "axis_exception" in shot:
            errors.append(f"shot {sid}: axis_exception alias unsupported; use camera.exception")
        for field in ("scene_id", "story_order", "edit_order", "production_order"):
            if field not in shot:
                errors.append(f"shot {sid}: {field} required")
        camera = shot.get("camera", {})
        if not isinstance(camera, dict):
            errors.append(f"shot {sid}: camera must be an object")
            camera = {}
        exception = camera.get("exception")
        if exception is not None:
            if not isinstance(exception, dict) or exception.get("type") != "deliberate" or not exception.get("reason") or not exception.get("evidence"):
                errors.append(f"shot {sid}: camera.exception requires type=deliberate, reason and evidence")
        if not camera.get("axis_id"):
            warnings.append(f"shot {sid}: camera.axis_id unspecified")
        shot_refs = shot.get("asset_refs", [])
        if not isinstance(shot_refs, list):
            errors.append(f"shot {sid}: asset_refs must be an array")
            shot_refs = []
        for ref in shot_refs:
            if not isinstance(ref, dict):
                errors.append(f"shot {sid}: invalid asset reference")
                continue
            aid = ref.get("asset_id")
            if aid not in asset_by_id:
                errors.append(f"shot {sid}: unknown asset {aid}")
            elif ref.get("state_version") != asset_by_id[aid].get("state_version"):
                errors.append(f"shot {sid}: state_version mismatch for {aid}")
        media = shot.get("media_evidence")
        if media:
            if not isinstance(media, dict) or not _sha256(media.get("sha256")):
                warnings.append(f"shot {sid}: malformed media receipt, not verified")
            else:
                warnings.append(f"shot {sid}: media receipt declared, not decoded/reviewed by this gate")

    mode = plan.get("mode")
    if mode in {"game", "hybrid"}:
        output["gameplay_status"] = "RUN_NOT_VERIFIED"
        any_trace = False
        if not gameplay:
            blockers.append("gameplay: executable scene and replay evidence missing")
        for index, item in enumerate(gameplay):
            if not isinstance(item, dict):
                errors.append(f"gameplay[{index}] invalid")
                continue
            gid = str(item.get("id", f"[{index}]"))
            if not item.get("engine"):
                errors.append(f"gameplay {gid}: engine required")
            game_refs = item.get("asset_refs", [])
            if not isinstance(game_refs, list):
                errors.append(f"gameplay {gid}: asset_refs must be an array")
                game_refs = []
            for aid in game_refs:
                if aid not in asset_by_id:
                    errors.append(f"gameplay {gid}: unknown asset {aid}")
            run = item.get("run_evidence")
            if (isinstance(run, dict) and _sha256(run.get("trace_sha256"))
                    and _sha256(run.get("build_sha256"))
                    and run.get("replayable") is True and run.get("assertions_passed") is True):
                any_trace = True
                warnings.append(f"gameplay {gid}: engine receipt only declared, execution not replayed")
            else:
                blockers.append(f"gameplay {gid}: reproducible engine run missing")
        if gameplay and any_trace and not any(x.startswith("gameplay") for x in blockers):
            output["gameplay_status"] = "RECEIPT_DECLARED_UNVERIFIED"

    for index, job in enumerate(provider_jobs):
        if not isinstance(job, dict):
            errors.append(f"provider_jobs[{index}] invalid")
            continue
        jid = str(job.get("id", f"[{index}]"))
        status = job.get("status")
        if status not in KNOWN_JOBS:
            errors.append(f"job {jid}: unknown status {status}")
            continue
        if status == "SUBMIT_UNKNOWN":
            jobs.append({"job_id": jid, "action": "RECONCILE_NO_RESUBMIT"})
            blockers.append(f"job {jid}: ambiguous provider submission, reconcile before retry")
        elif status in {"RUNNING", "SUBMITTED"}:
            jobs.append({"job_id": jid, "action": "POLL_EXISTING_ID"})
        else:
            jobs.append({"job_id": jid, "action": "NO_AUTOMATIC_SUBMISSION"})

    for index, cycle in enumerate(repair_cycles):
        if not isinstance(cycle, dict):
            errors.append(f"repair_cycles[{index}] invalid")
            continue
        target = cycle.get("target")
        attempts = cycle.get("attempts")
        maximum = cycle.get("max_attempts")
        if not target or not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 0 or not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 1:
            errors.append(f"repair_cycles[{index}] requires target, attempts>=0 and max_attempts>=1")
            continue
        repairs.append({"target": target, "action": "ESCALATE_HUMAN" if attempts >= maximum else "REPAIR_SCOPE_ONLY",
                        "remaining_attempts": max(0, maximum - attempts)})

    output["delivery_status"] = "RIGHTS_RECORDED_UNVERIFIED" if rights_ok else "RIGHTS_PENDING"
    output["status"] = "BLOCKED" if errors or any("ambiguous provider submission" in b for b in blockers) else "PLAN_READY"
    if not rights_ok:
        output["status"] = "BLOCKED"
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path, help="JSON plan file")
    parser.add_argument("--out", type=Path, help="Output report JSON (optional)")
    args = parser.parse_args()
    try:
        data = json.loads(args.plan.read_text(encoding="utf-8"))
        result = evaluate_plan(data)
    except (OSError, json.JSONDecodeError) as e:
        result = {"status": "BLOCKED", "errors": [f"input error: {e}"], "generation_authorized": False}
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 2 if result["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
