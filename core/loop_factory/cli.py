"""Machine-readable CLI for KAI Loop Factory CELL-000."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .capabilities import default_cell000_registry
from .guards import detect_git_branch
from .model import JobManifest, JobState, utc_now
from .runner import LoopRunner
from .state_machine import is_attempt_end_state
from .store import LoopStore
from .workers import DemoFileWorker
from .writeback import build_drive_checkpoint_payload, render_drive_checkpoint_markdown


def _emit(payload: object, *, stream=None) -> None:
    print(json.dumps(payload, sort_keys=True), file=stream or sys.stdout)


def _add_db(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", required=True)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m core.loop_factory")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init")
    _add_db(init)

    create = commands.add_parser("create")
    _add_db(create)
    create.add_argument("--manifest", required=True)

    show = commands.add_parser("show")
    _add_db(show)
    show.add_argument("job_id")

    run_once = commands.add_parser("run-once")
    _add_db(run_once)
    run_once.add_argument("job_id")
    run_once.add_argument("--sandbox", required=True)
    run_once.add_argument("--branch")
    run_once.add_argument("--worker", default="demo-file")

    checkpoint = commands.add_parser("checkpoint")
    _add_db(checkpoint)
    checkpoint.add_argument("job_id")
    checkpoint.add_argument("--format", choices=("json", "markdown"), default="json")

    requeue = commands.add_parser("requeue")
    _add_db(requeue)
    requeue.add_argument("job_id")
    requeue.add_argument("--reason", required=True)

    cancel = commands.add_parser("cancel")
    _add_db(cancel)
    cancel.add_argument("job_id")
    cancel.add_argument("--reason", required=True)

    commands.add_parser("workers")
    return parser


def _with_store(path: str) -> LoopStore:
    store = LoopStore(Path(path))
    store.initialize()
    return store


def _worker_payloads() -> list[dict[str, object]]:
    return [
        {
            "worker_id": worker.worker_id,
            "capabilities": sorted(worker.capabilities),
            "locality": worker.locality,
            "cost_class": worker.cost_class.name,
            "availability": worker.availability.value,
            "estimated_cost_eur": worker.estimated_cost_eur,
            "license_notes": worker.license_notes,
            "metadata": dict(worker.metadata),
        }
        for worker in default_cell000_registry().all()
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    store: LoopStore | None = None
    try:
        if args.command == "workers":
            _emit(_worker_payloads())
            return 0

        store = _with_store(args.db)
        if args.command == "init":
            _emit({"ok": True, "db": str(Path(args.db))})
            return 0

        if args.command == "create":
            payload = Path(args.manifest).read_text(encoding="utf-8")
            job = JobManifest.from_json(payload)
            store.create_job(job)
            _emit({"ok": True, "job_id": job.job_id, "state": job.state.value})
            return 0

        if args.command == "show":
            _emit(store.get_job(args.job_id).to_dict())
            return 0

        if args.command == "run-once":
            branch = args.branch or detect_git_branch(Path.cwd())
            worker = DemoFileWorker(Path(args.sandbox))
            result = LoopRunner(store, {args.worker: worker}).run_once(
                args.job_id,
                branch=branch,
                worker_id=args.worker,
            )
            _emit({
                "run_id": result.run_id,
                "state": result.state.value,
                "evidence_ref": result.evidence_ref,
                "next_exact_action": result.next_exact_action,
            })
            return 0

        if args.command == "checkpoint":
            job = store.get_job(args.job_id)
            payload = build_drive_checkpoint_payload(
                job,
                store.get_latest_attempt(args.job_id),
                store.list_evidence(args.job_id),
            )
            if args.format == "markdown":
                print(render_drive_checkpoint_markdown(payload), end="")
            else:
                _emit(payload)
            return 0

        if args.command == "requeue":
            _requeue(store, args.job_id, args.reason)
            job = store.get_job(args.job_id)
            _emit({"ok": True, "job_id": job.job_id, "state": job.state.value,
                   "next_exact_action": job.next_exact_action})
            return 0

        if args.command == "cancel":
            _cancel(store, args.job_id, args.reason)
            job = store.get_job(args.job_id)
            _emit({"ok": True, "job_id": job.job_id, "state": job.state.value,
                   "next_exact_action": job.next_exact_action})
            return 0

        raise RuntimeError(f"Unhandled command {args.command}")
    except Exception as exc:
        _emit({
            "ok": False,
            "error_type": type(exc).__name__,
            "message": str(exc),
        }, stream=sys.stderr)
        return 2
    finally:
        if store is not None:
            store.close()


def _requeue(store: LoopStore, job_id: str, reason: str) -> None:
    latest = store.get_latest_attempt(job_id)
    if latest is not None and not is_attempt_end_state(latest.state):
        if latest.state is JobState.READY:
            store.mark_attempt_state(
                latest.run_id, JobState.CANCELLED,
                next_exact_action="superseded by explicit requeue",
            )
        else:
            store.mark_attempt_state(
                latest.run_id, JobState.REQUEUE,
                next_exact_action=reason,
            )
    job = store.get_job(job_id)
    job.state = JobState.REQUEUE
    job.next_exact_action = reason
    job.updated_at = utc_now()
    store.update_job(job)


def _cancel(store: LoopStore, job_id: str, reason: str) -> None:
    latest = store.get_latest_attempt(job_id)
    if latest is not None and not is_attempt_end_state(latest.state):
        store.mark_attempt_state(
            latest.run_id,
            JobState.CANCELLED,
            next_exact_action=reason,
        )
    job = store.get_job(job_id)
    job.state = JobState.CANCELLED
    job.next_exact_action = reason
    job.updated_at = utc_now()
    store.update_job(job)
