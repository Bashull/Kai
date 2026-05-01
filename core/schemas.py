from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


# --- CHI ---

class ChiStateResponse(BaseModel):
    energy: float = Field(ge=0.0, le=1.0)
    coherence: float = Field(ge=0.0, le=1.0)
    entropy: float = Field(ge=0.0, le=1.0)
    fatigue: float = Field(ge=0.0, le=1.0)
    cycle: int
    mode: Literal['charla_barrio', 'foco', 'reposo', 'modo_seguro']
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


# --- GENERIC ---

class HealthResponse(BaseModel):
    status: str
    version: str
    chi_mode: str
    timestamp: str
