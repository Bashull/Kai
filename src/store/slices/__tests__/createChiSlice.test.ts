import { describe, it, expect, beforeEach } from 'vitest';
import { createStore } from 'zustand';
import { createChiSlice, initialChiState } from '../createChiSlice';
import { ChiSlice } from '../../../types';

function makeStore() {
  return createStore<ChiSlice>()((...a) => createChiSlice(...a));
}

describe('createChiSlice — estado inicial', () => {
  it('arranca con valores nominales', () => {
    const store = makeStore();
    const { chi } = store.getState();
    expect(chi.energy).toBeGreaterThan(0.7);
    expect(chi.coherence).toBeGreaterThan(0.8);
    expect(chi.entropy).toBeLessThan(0.3);
    expect(chi.mode).toBe('charla_barrio');
  });

  it('el audit inicial es OPTIMO', () => {
    const store = makeStore();
    expect(store.getState().chiAudit.severity).toBe('OPTIMO');
  });
});

describe('adjustChi', () => {
  it('aplica deltas y actualiza el ciclo', () => {
    const store = makeStore();
    const { cycle: before } = store.getState().chi;
    store.getState().adjustChi({ energy: -0.1, fatigue: 0.2 });
    const { chi } = store.getState();
    expect(chi.cycle).toBe(before + 1);
    expect(chi.energy).toBeCloseTo(initialChiState.energy - 0.1, 3);
    expect(chi.fatigue).toBeCloseTo(initialChiState.fatigue + 0.2, 3);
  });

  it('clampea los valores entre 0 y 1', () => {
    const store = makeStore();
    store.getState().adjustChi({ energy: -999, coherence: 999 });
    const { chi } = store.getState();
    expect(chi.energy).toBe(0);
    expect(chi.coherence).toBe(1);
  });

  it('deriva modo_seguro cuando coherencia cae por debajo de 0.45', () => {
    const store = makeStore();
    const drop = initialChiState.coherence - 0.44;
    store.getState().adjustChi({ coherence: -drop });
    expect(store.getState().chi.mode).toBe('modo_seguro');
  });

  it('deriva modo_seguro cuando entropía supera 0.82', () => {
    const store = makeStore();
    const rise = 0.83 - initialChiState.entropy;
    store.getState().adjustChi({ entropy: rise });
    expect(store.getState().chi.mode).toBe('modo_seguro');
  });

  it('deriva foco cuando coherencia > 0.82 y entropía < 0.35', () => {
    const store = makeStore();
    // estado inicial ya tiene coherence=0.86, entropy=0.22 → foco
    expect(store.getState().chi.mode).toBe('charla_barrio');
    // aplicar un ajuste mínimo para re-derivar
    store.getState().adjustChi({});
    expect(store.getState().chi.mode).toBe('foco');
  });

  it('genera audit CRITICO cuando coherencia es muy baja', () => {
    const store = makeStore();
    store.getState().adjustChi({ coherence: -0.8 });
    expect(store.getState().chiAudit.severity).toBe('CRITICO');
  });

  it('genera audit ALERTA cuando entropía es alta', () => {
    const store = makeStore();
    store.getState().adjustChi({ entropy: 0.55 });
    expect(store.getState().chiAudit.severity).toBe('ALERTA');
  });
});

describe('restoreChi', () => {
  it('incrementa energía y coherencia, reduce entropía y fatiga', () => {
    const store = makeStore();
    // Degradar primero
    store.getState().adjustChi({ energy: -0.3, coherence: -0.3, entropy: 0.4, fatigue: 0.4 });
    const before = store.getState().chi;

    store.getState().restoreChi();
    const after = store.getState().chi;

    expect(after.energy).toBeGreaterThan(before.energy);
    expect(after.coherence).toBeGreaterThan(before.coherence);
    expect(after.entropy).toBeLessThan(before.entropy);
    expect(after.fatigue).toBeLessThan(before.fatigue);
    expect(after.lastAlert).toBe('RESTAURADO');
  });

  it('no supera 1.0 tras restaurar desde estado casi pleno', () => {
    const store = makeStore();
    store.getState().restoreChi();
    const { chi } = store.getState();
    expect(chi.energy).toBeLessThanOrEqual(1);
    expect(chi.coherence).toBeLessThanOrEqual(1);
  });
});

describe('auditChi', () => {
  it('devuelve el audit actual sin mutarlo innecesariamente', () => {
    const store = makeStore();
    const audit = store.getState().auditChi();
    expect(audit).toBeDefined();
    expect(['OPTIMO', 'ALERTA', 'CRITICO']).toContain(audit.severity);
  });
});
