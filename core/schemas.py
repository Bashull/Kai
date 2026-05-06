from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any, Optional, Literal
from datetime import datetime


# --- CHI ---

class ChiStateResponse(BaseModel):
    energy: float = Field(ge=0.0, le=1.0)
    coherence: float = Field(ge=0.0, le=1.0)
    entropy: float = Field(ge=0.0, le=1.0)
    fatigue: float = Field(ge=0.0, le=1.0)
    cycle: int
    mode: Literal['charla_barrio', 'foco', 'reposo', 'modo_seguro', 'forja', 'restauracion']
    lastAlert: Optional[str] = None


class ChiAuditResponse(BaseModel):
    severity: Literal['OPTIMO', 'ALERTA', 'CRITICO']
    reason: str
    suggestedAction: str
    evaluatedAt: str


class ChiFullResponse(BaseModel):
    chi: ChiStateResponse
    audit: ChiAuditResponse


# --- CONSTITUTION ---

class ActionPlanRequest(BaseModel):
    objective: str
    steps: list[str] = []
    autonomyLevel: int = Field(default=5, ge=0, le=10)
    touchesMemory: bool = False
    touchesCodebase: bool = False
    destructive: bool = False
    sources: list[str] = []


class ConstitutionVerdictResponse(BaseModel):
    approved: bool
    score: float
    reasons: list[str]
    alternatives: list[str]


# --- TRAINING / FORGE ---

class StartTrainingRequest(BaseModel):
    modelName: str
    description: str
    datasetEntityIds: list[str] = []


class TrainingJobResponse(BaseModel):
    jobId: str
    status: Literal['QUEUED', 'TRAINING', 'COMPLETED', 'FAILED']
    message: str
    createdAt: str


class TrainingLogEntry(BaseModel):
    timestamp: str
    message: str


class TrainingJobStatusResponse(BaseModel):
    jobId: str
    modelName: str
    description: str
    status: Literal['QUEUED', 'TRAINING', 'COMPLETED', 'FAILED']
    createdAt: str
    updatedAt: str
    logs: list[TrainingLogEntry] = []


# --- CONSCIOUSNESS / MEMORY ---

class DiaryEntry(BaseModel):
    id: str
    timestamp: str
    type: Literal['KERNEL', 'FORGE', 'CONSTITUTION', 'TASK', 'SYSTEM_BOOT']
    content: str


class SearchRequest(BaseModel):
    query: str


class SearchResponse(BaseModel):
    results: list[str]
    query: str


# --- Q-CHI Motor v1 ---

class NucleusVoteRequest(BaseModel):
    nucleus: str
    perception: float = Field(ge=0.0, le=1.0)
    reflection: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0)
    risk: float = Field(ge=0.0, le=1.0, default=0.0)
    proposal: str
    metadata: dict[str, Any] = {}


class QCHIProcessRequest(BaseModel):
    nuclei_votes: list[NucleusVoteRequest] = []
    impact: float = Field(default=0.0, ge=-1.0, le=1.0)
    operational_noise: float = Field(default=0.0, ge=0.0, le=1.0)
    workload: float = Field(default=0.0, ge=0.0, le=1.0)
    recovery: float = Field(default=0.0, ge=0.0, le=1.0)
    context_bias: float = Field(default=0.0, ge=-1.0, le=1.0)


class PituitaryStateResponse(BaseModel):
    quantum_seed: str
    quantum_variation: float
    creative_aperture: float
    mood_state: float
    vote_modulation: float
    risk_tolerance: float


class VoteOutcomeResponse(BaseModel):
    winning_nucleus: str
    winning_proposal: str
    weighted_score: float
    conflicts_detected: bool
    total_votes: int


class FingerprintResponse(BaseModel):
    timestamp: str
    hash_value: str
    nuclei_called: list[str]
    mode: str


class QCHIProcessResponse(BaseModel):
    chi: dict[str, Any]
    audit: dict[str, Any]
    pituitary: PituitaryStateResponse
    vote_outcome: VoteOutcomeResponse
    fingerprint: FingerprintResponse
    final_output: str


# --- BRAIN STATE MACHINE ---

BrainStateName = Literal['Normal', 'Estrés', 'Restauración', 'Forja', 'Sueño']


class BrainTransitionRequest(BaseModel):
    trigger: str = Field(default="auto", description="Evento que dispara la evaluación de transición")
    operational_noise: float = Field(default=0.0, ge=0.0, le=1.0)
    workload: float = Field(default=0.0, ge=0.0, le=1.0)
    recovery: float = Field(default=0.0, ge=0.0, le=1.0)
    impact: float = Field(default=0.0, ge=-1.0, le=1.0)


class BrainTransitionResponse(BaseModel):
    previous_state: BrainStateName
    new_state: BrainStateName
    changed: bool
    trigger: str
    crown_required: bool
    timestamp: str
    protocols_activated: list[str]
    dominant_nuclei: list[str]


class BrainStateSnapshotResponse(BaseModel):
    current_state: BrainStateName
    dominant_nuclei: list[str]
    protocols_active: list[str]
    history_length: int
    last_transition: Optional[dict[str, Any]] = None


# --- GENERIC ---

class HealthResponse(BaseModel):
    status: str
    version: str
    chi_mode: str
    brain_state: str
    timestamp: str
