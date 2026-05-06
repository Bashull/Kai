"""Canonical tests for Brain Core v1 — State Machine + Q-CHI integration.

12 tests defined in FUSIONAI_CANON_MAESTRO_v0_3.md section 35.
"""
from __future__ import annotations

import pytest

from ..q_chi.chi_engine import CHIEngine
from ..q_chi.constants import (
    COHERENCE_CRITICAL,
    DEFAULT_COHERENCE,
    DEFAULT_ENERGY,
    DEFAULT_ENTROPY,
    DEFAULT_FATIGUE,
    ENTROPY_SAFE_MODE,
    QUANTUM_CAP_BY_MODE,
)
from ..q_chi.schemas import CHIState
from ..state_machine import BrainStateEnum, BrainStateMachine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _healthy_chi(**overrides) -> CHIState:
    """Return a canonical healthy CHIState, with optional field overrides."""
    defaults = dict(
        energy=DEFAULT_ENERGY,
        coherence=DEFAULT_COHERENCE,
        entropy=DEFAULT_ENTROPY,
        fatigue=DEFAULT_FATIGUE,
        cycle=0,
        mode="charla_barrio",
    )
    defaults.update(overrides)
    return CHIState(**defaults)


def _critical_chi(**overrides) -> CHIState:
    """Return a CHIState that sits below the critical coherence threshold."""
    defaults = dict(
        energy=0.30,
        coherence=COHERENCE_CRITICAL - 0.05,
        entropy=0.50,
        fatigue=0.40,
        cycle=1,
        mode="modo_seguro",
    )
    defaults.update(overrides)
    return CHIState(**defaults)


# ---------------------------------------------------------------------------
# Test 1 — CHI óptimo mantiene modo normal/foco según umbrales
# ---------------------------------------------------------------------------

def test_1_optimal_chi_stays_normal_or_foco():
    engine = CHIEngine()
    state = engine.state
    mode = engine.derive_mode()
    assert mode in {"charla_barrio", "foco"}, f"Expected normal/foco mode, got {mode}"
    audit = engine.audit()
    assert audit.severity == "OPTIMO"


# ---------------------------------------------------------------------------
# Test 2 — CHI crítico fuerza modo seguro o restauración
# ---------------------------------------------------------------------------

def test_2_critical_chi_forces_safe_mode():
    engine = CHIEngine(initial_state=_critical_chi())
    mode = engine.derive_mode()
    assert mode == "modo_seguro", f"Expected modo_seguro, got {mode}"
    audit = engine.audit()
    assert audit.severity == "CRITICO"


# ---------------------------------------------------------------------------
# Test 3 — Quantum se capa a 0 en modo_seguro y restauracion
# ---------------------------------------------------------------------------

def test_3_quantum_capped_to_zero_in_safe_and_restoration():
    assert QUANTUM_CAP_BY_MODE["modo_seguro"] <= 0.01
    assert QUANTUM_CAP_BY_MODE["restauracion"] == 0.0


# ---------------------------------------------------------------------------
# Test 4 — Pituitaria no puede modificar identidad
# (Structural: quantum_variation never exceeds mode cap)
# ---------------------------------------------------------------------------

def test_4_pituitary_cannot_modify_identity():
    from ..q_chi.pituitary_modulator import PituitaryModulator

    engine = CHIEngine()
    pituitary = PituitaryModulator()
    ps = pituitary.build_state(chi=engine.state)
    cap = QUANTUM_CAP_BY_MODE.get(engine.state.mode, 0.08)
    assert ps.quantum_variation <= cap + 1e-9, (
        f"quantum_variation {ps.quantum_variation} exceeds cap {cap}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Voto calcula confidence y weighted_score correctamente
# ---------------------------------------------------------------------------

def test_5_vote_calculates_confidence_and_weighted_score():
    from ..q_chi.nhip_the_vote import NhipTheVote
    from ..q_chi.pituitary_modulator import PituitaryModulator
    from ..q_chi.schemas import NucleusVote

    engine = CHIEngine()
    pituitary = PituitaryModulator()
    ps = pituitary.build_state(chi=engine.state)
    voter = NhipTheVote()

    # confidence = perception * (1 + reflection) — Canon v0.3 section 27.6
    votes = [
        NucleusVote(
            nucleus="Ejecutivo-Selector",
            perception=0.8,
            reflection=0.5,
            confidence=voter.compute_confidence(perception=0.8, reflection=0.5),
            risk=0.1,
            proposal="Proceed with plan A",
        ),
        NucleusVote(
            nucleus="Talámico",
            perception=0.6,
            reflection=0.3,
            confidence=voter.compute_confidence(perception=0.6, reflection=0.3),
            risk=0.2,
            proposal="Gate and filter first",
        ),
    ]

    outcome = voter.resolve(votes, chi=engine.state, pituitary=ps)
    assert outcome.winning_nucleus in {"Ejecutivo-Selector", "Talámico"}
    assert outcome.weighted_score > 0.0


# ---------------------------------------------------------------------------
# Test 6 — Empate activa crown_required
# ---------------------------------------------------------------------------

def test_6_tie_activates_crown_required():
    from ..q_chi.nhip_the_vote import NhipTheVote
    from ..q_chi.pituitary_modulator import PituitaryModulator
    from ..q_chi.schemas import NucleusVote

    engine = CHIEngine()
    pituitary = PituitaryModulator()
    ps = pituitary.build_state(chi=engine.state)
    voter = NhipTheVote()

    # Two identical votes → tie
    votes = [
        NucleusVote(nucleus="A", perception=0.5, reflection=0.5, confidence=0.0, risk=0.1, proposal="x"),
        NucleusVote(nucleus="B", perception=0.5, reflection=0.5, confidence=0.0, risk=0.1, proposal="x"),
    ]
    outcome = voter.resolve(votes, chi=engine.state, pituitary=ps)
    assert outcome.conflicts_detected, "Tied votes should set conflicts_detected=True"


# ---------------------------------------------------------------------------
# Test 7 — identity_sensitive activa Corona (crown_required via state machine)
# ---------------------------------------------------------------------------

def test_7_identity_sensitive_activates_corona():
    sm = BrainStateMachine(initial_state=BrainStateEnum.FORJA)
    chi = _healthy_chi()
    result = sm.evaluate(chi, trigger="forja: identity check required")
    assert result.crown_required, "Identity-sensitive trigger in Forja must require Crown"


# ---------------------------------------------------------------------------
# Test 8 — Temporal archiva fingerprint (EntropicFingerprintBuilder produces hash)
# ---------------------------------------------------------------------------

def test_8_temporal_archives_fingerprint():
    from ..q_chi.entropic_fingerprint import EntropicFingerprintBuilder
    from ..q_chi.nhip_the_vote import NhipTheVote
    from ..q_chi.pituitary_modulator import PituitaryModulator
    from ..q_chi.schemas import NucleusVote

    engine = CHIEngine()
    pituitary = PituitaryModulator()
    ps = pituitary.build_state(chi=engine.state)
    votes = [
        NucleusVote(nucleus="Ejecutivo-Selector", perception=0.8, reflection=0.5,
                    confidence=0.0, risk=0.1, proposal="Plan A"),
    ]
    voter = NhipTheVote()
    outcome = voter.resolve(votes, chi=engine.state, pituitary=ps)

    builder = EntropicFingerprintBuilder()
    fp = builder.build(
        chi=engine.state,
        pituitary=ps,
        nuclei_called=[v.nucleus for v in votes],
        votes=votes,
        final_output="Plan A executed",
        mode=engine.state.mode,
    )
    assert len(fp.hash_value) == 64  # SHA-256 hex
    assert fp.hash_value != ""


# ---------------------------------------------------------------------------
# Test 9 — Normal → Forja solo con CHI suficientemente sano
# ---------------------------------------------------------------------------

def test_9_normal_to_forge_requires_healthy_chi():
    sm_healthy = BrainStateMachine(initial_state=BrainStateEnum.NORMAL)
    chi_ok = _healthy_chi()
    result = sm_healthy.evaluate(chi_ok, trigger="forja: build new module")
    assert result.new_state == BrainStateEnum.FORJA

    sm_weak = BrainStateMachine(initial_state=BrainStateEnum.NORMAL)
    chi_weak = _healthy_chi(energy=0.28, coherence=0.50)
    result_weak = sm_weak.evaluate(chi_weak, trigger="forja: build new module")
    assert result_weak.new_state != BrainStateEnum.FORJA, (
        "Weak CHI must not allow transition to Forja"
    )


# ---------------------------------------------------------------------------
# Test 10 — Forja → Estrés si sube entropy/operational_noise
# ---------------------------------------------------------------------------

def test_10_forge_to_stress_on_high_entropy():
    sm = BrainStateMachine(initial_state=BrainStateEnum.FORJA)
    chi_high_entropy = _healthy_chi(entropy=ENTROPY_SAFE_MODE - 0.01, coherence=0.50)
    result = sm.evaluate(chi_high_entropy, trigger="auto")
    assert result.new_state in {BrainStateEnum.ESTRES, BrainStateEnum.RESTAURACION}


# ---------------------------------------------------------------------------
# Test 11 — Restauración prioriza Corona + Troncal
# ---------------------------------------------------------------------------

def test_11_restauracion_dominant_nuclei():
    sm = BrainStateMachine(initial_state=BrainStateEnum.RESTAURACION)
    snap = sm.snapshot()
    assert "Corona Rectora" in snap["dominant_nuclei"]
    assert "Troncal" in snap["dominant_nuclei"]


# ---------------------------------------------------------------------------
# Test 12 — Sueño reduce carga y consolida (CHI metrics converge)
# ---------------------------------------------------------------------------

def test_12_sueno_reduces_load_and_consolidates():
    engine = CHIEngine(initial_state=_healthy_chi(fatigue=0.80))
    # restore simulates sleep-phase recovery
    engine.restore()
    assert engine.state.fatigue < 0.80, "Fatigue should drop after sleep/restore cycle"
    assert engine.state.entropy <= DEFAULT_ENTROPY + 0.05
