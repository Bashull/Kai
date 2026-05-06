"""
KaiOS v3.0 — FastAPI Backend
Expone el núcleo cognitivo Python (CHI + Constitución) al frontend React.

Arrancar en desarrollo:
    cd core && uvicorn main:app --reload --host 0.0.0.0 --port 8000

Variables de entorno (copiar core/.env.example → core/.env):
    GEMINI_API_KEY, DATABASE_URL, REDIS_URL, CORS_ORIGINS
"""

from __future__ import annotations

import os
import uuid
import time
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from chi_engine import CHIEngine
from constitution_engine import ConstitutionEngine
from brain.q_chi import (
    CHIEngine as QCHIEngine,
    EntropicFingerprintBuilder,
    NhipTheVote,
    NucleusVote,
    PituitaryModulator,
    QCHIRuntime,
)
from brain.state_machine import BrainStateMachine, BrainStateEnum
from schemas import (
    ActionPlanRequest,
    BrainStateSnapshotResponse,
    BrainTransitionRequest,
    BrainTransitionResponse,
    ChiAuditResponse,
    ChiFullResponse,
    ChiStateResponse,
    ConstitutionVerdictResponse,
    DiaryEntry,
    FingerprintResponse,
    HealthResponse,
    NucleusVoteRequest,
    PituitaryStateResponse,
    QCHIProcessRequest,
    QCHIProcessResponse,
    SearchResponse,
    StartTrainingRequest,
    TrainingJobResponse,
    TrainingJobStatusResponse,
    TrainingLogEntry,
    VoteOutcomeResponse,
)

load_dotenv()

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000",
).split(",")

app = FastAPI(
    title="KaiOS API",
    description="Núcleo cognitivo de KaiOS v3.0 — CHI, Constitución y Consciencia",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------

chi_engine = CHIEngine()
constitution_engine = ConstitutionEngine()

# Q-CHI Motor v1 — wired runtime
_qchi_engine = QCHIEngine()
_qchi_runtime = QCHIRuntime(
    chi_engine=_qchi_engine,
    pituitary=PituitaryModulator(),
    voter=NhipTheVote(),
    fingerprint_builder=EntropicFingerprintBuilder(),
)

# Brain Core v1 — State Machine
_brain_sm = BrainStateMachine()

# In-memory diary and training store (replace with DB in production)
_diary: list[dict] = []
_training_jobs: dict[str, dict] = {}

MOCK_LOGS = [
    "Epoch 1/10 - loss: 1.234, accuracy: 0.65",
    "Epoch 2/10 - loss: 0.987, accuracy: 0.72",
    "Epoch 3/10 - loss: 0.765, accuracy: 0.78",
    "Epoch 4/10 - loss: 0.654, accuracy: 0.81",
    "Epoch 5/10 - loss: 0.543, accuracy: 0.85",
    "Epoch 6/10 - loss: 0.432, accuracy: 0.88",
    "Epoch 7/10 - loss: 0.321, accuracy: 0.91",
    "Epoch 8/10 - loss: 0.210, accuracy: 0.94",
    "Epoch 9/10 - loss: 0.150, accuracy: 0.96",
    "Epoch 10/10 - loss: 0.100, accuracy: 0.98",
    "Model training completed successfully.",
    "Saving model artifacts...",
]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    snap = chi_engine.snapshot()
    brain_snap = _brain_sm.snapshot()
    return HealthResponse(
        status="ok",
        version="3.0.0",
        chi_mode=snap.get("mode", "unknown"),
        brain_state=brain_snap["current_state"],
        timestamp=datetime.now().isoformat(),
    )


# ---------------------------------------------------------------------------
# CHI — Homeostasis
# ---------------------------------------------------------------------------

@app.get("/api/consciousness/state", response_model=ChiFullResponse, tags=["chi"])
async def get_chi_state():
    snap = chi_engine.snapshot()
    audit = chi_engine.audit()
    return ChiFullResponse(
        chi=ChiStateResponse(**snap),
        audit=ChiAuditResponse(**audit),
    )


@app.post("/api/consciousness/restore", response_model=ChiFullResponse, tags=["chi"])
async def restore_chi():
    chi_engine.restore()
    snap = chi_engine.snapshot()
    audit = chi_engine.audit()
    return ChiFullResponse(
        chi=ChiStateResponse(**snap),
        audit=ChiAuditResponse(**audit),
    )


# ---------------------------------------------------------------------------
# Constitution — Guardia ética
# ---------------------------------------------------------------------------

@app.post("/api/constitution/evaluate", response_model=ConstitutionVerdictResponse, tags=["constitution"])
async def evaluate_plan(body: ActionPlanRequest):
    plan = {
        "objective": body.objective,
        "steps": body.steps,
        "autonomy_level": body.autonomyLevel,
        "touches_memory": body.touchesMemory,
        "touches_codebase": body.touchesCodebase,
        "destructive": body.destructive,
        "sources": body.sources,
    }
    verdict = constitution_engine.evaluate_plan(plan)
    return ConstitutionVerdictResponse(
        approved=verdict.get("approved", False),
        score=verdict.get("score", 0.0),
        reasons=verdict.get("reasons", []),
        alternatives=verdict.get("alternatives", []),
    )


# ---------------------------------------------------------------------------
# Consciousness — Memoria y Diario
# ---------------------------------------------------------------------------

@app.get("/api/consciousness/memories", tags=["consciousness"])
async def get_memories():
    return {"memories": _diary, "total": len(_diary)}


@app.get("/api/consciousness/diary", tags=["consciousness"])
async def get_diary():
    return {"entries": _diary, "total": len(_diary)}


@app.post("/api/consciousness/diary", response_model=DiaryEntry, tags=["consciousness"])
async def add_diary_entry(entry: DiaryEntry):
    _diary.append(entry.model_dump())
    return entry


@app.get("/api/consciousness/snapshots", tags=["consciousness"])
async def get_snapshots():
    chi_snap = chi_engine.snapshot()
    return {
        "snapshots": [
            {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "chi": chi_snap,
            }
        ]
    }


@app.get("/api/consciousness/search", tags=["consciousness"])
async def search_memories(query: str):
    query_lower = query.lower()
    results = [
        e["content"] for e in _diary
        if query_lower in e.get("content", "").lower()
    ]
    return SearchResponse(results=results, query=query)


@app.post("/api/consciousness/memory/compile", tags=["consciousness"])
async def compile_memory():
    snap = chi_engine.snapshot()
    return {
        "compiled_at": datetime.now().isoformat(),
        "total_entries": len(_diary),
        "chi_snapshot": snap,
        "message": "memoria_kai.json compilada correctamente.",
    }


# ---------------------------------------------------------------------------
# Forge — Entrenamiento
# ---------------------------------------------------------------------------

@app.post("/api/forge/start-training", response_model=TrainingJobResponse, tags=["forge"])
async def start_training(body: StartTrainingRequest):
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()
    _training_jobs[job_id] = {
        "jobId": job_id,
        "modelName": body.modelName,
        "description": body.description,
        "status": "QUEUED",
        "createdAt": now,
        "updatedAt": now,
        "logs": [{"timestamp": now, "message": "Training job queued."}],
        "_created_ts": time.time(),
    }
    return TrainingJobResponse(
        jobId=job_id,
        status="QUEUED",
        message="Training job successfully queued.",
        createdAt=now,
    )


@app.get("/api/forge/jobs/{job_id}", response_model=TrainingJobStatusResponse, tags=["forge"])
async def get_training_job(job_id: str):
    job = _training_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    # Simulate progression based on elapsed time
    elapsed = time.time() - job["_created_ts"]
    epoch_index = min(int(elapsed / 5), len(MOCK_LOGS))

    if job["status"] == "QUEUED" and elapsed > 3:
        job["status"] = "TRAINING"
        job["updatedAt"] = datetime.now().isoformat()

    if job["status"] == "TRAINING":
        current_logs = len(job["logs"])
        if epoch_index >= current_logs and epoch_index <= len(MOCK_LOGS):
            for i in range(current_logs, epoch_index):
                job["logs"].append({
                    "timestamp": datetime.now().isoformat(),
                    "message": MOCK_LOGS[i],
                })
            job["updatedAt"] = datetime.now().isoformat()

        if epoch_index > len(MOCK_LOGS):
            job["status"] = "COMPLETED"
            job["updatedAt"] = datetime.now().isoformat()

    return TrainingJobStatusResponse(
        jobId=job["jobId"],
        modelName=job["modelName"],
        description=job["description"],
        status=job["status"],
        createdAt=job["createdAt"],
        updatedAt=job["updatedAt"],
        logs=[TrainingLogEntry(**l) for l in job["logs"]],
    )


# ---------------------------------------------------------------------------
# Q-CHI Motor v1 — Cerebro canónico
# ---------------------------------------------------------------------------

@app.get("/api/qchi/state", tags=["qchi"])
async def get_qchi_state():
    snap = _qchi_runtime.snapshot()
    audit = _qchi_runtime.audit()
    return {"chi": snap, "audit": audit}


@app.post("/api/qchi/restore", tags=["qchi"])
async def restore_qchi():
    snap = _qchi_runtime.restore()
    audit = _qchi_runtime.audit()
    return {"chi": snap, "audit": audit}


@app.post("/api/qchi/process", response_model=QCHIProcessResponse, tags=["qchi"])
async def process_qchi(body: QCHIProcessRequest):
    votes = [
        NucleusVote(
            nucleus=v.nucleus,
            perception=v.perception,
            reflection=v.reflection,
            confidence=v.confidence,
            risk=v.risk,
            proposal=v.proposal,
            metadata=v.metadata,
        )
        for v in body.nuclei_votes
    ]
    result = _qchi_runtime.process(
        input_payload={},
        nuclei_votes=votes,
        impact=body.impact,
        operational_noise=body.operational_noise,
        workload=body.workload,
        recovery=body.recovery,
        context_bias=body.context_bias,
    )
    return QCHIProcessResponse(
        chi=result["chi"],
        audit=result["audit"],
        pituitary=PituitaryStateResponse(**result["pituitary"]),
        vote_outcome=VoteOutcomeResponse(**result["vote_outcome"]),
        fingerprint=FingerprintResponse(**result["fingerprint"]),
        final_output=result["final_output"],
    )


# ---------------------------------------------------------------------------
# Brain Core v1 — State Machine
# ---------------------------------------------------------------------------

@app.get("/api/brain/state", response_model=BrainStateSnapshotResponse, tags=["brain"])
async def get_brain_state():
    snap = _brain_sm.snapshot()
    return BrainStateSnapshotResponse(**snap)


@app.post("/api/brain/transition", response_model=BrainTransitionResponse, tags=["brain"])
async def brain_transition(body: BrainTransitionRequest):
    # Apply operational inputs to the shared Q-CHI engine so CHI reflects reality
    _qchi_engine.adjust(
        impact=body.impact,
        operational_noise=body.operational_noise,
        workload=body.workload,
        recovery=body.recovery,
    )
    chi = _qchi_engine.state
    result = _brain_sm.evaluate(chi, trigger=body.trigger)
    return BrainTransitionResponse(
        previous_state=result.previous_state.value,
        new_state=result.new_state.value,
        changed=result.changed,
        trigger=result.trigger,
        crown_required=result.crown_required,
        timestamp=result.timestamp,
        protocols_activated=result.protocols_activated,
        dominant_nuclei=result.dominant_nuclei,
    )
