import { AppSlice, ChiSlice, ChiState, ChiAudit, ChiMode } from '../../types';

export const initialChiState: ChiState = {
  energy: 0.78,
  coherence: 0.86,
  entropy: 0.22,
  fatigue: 0.08,
  cycle: 0,
  mode: 'charla_barrio',
  lastAlert: null,
};

function clamp(value: number): number {
  return Math.max(0, Math.min(1, Number(value.toFixed(4))));
}

function deriveMode(state: ChiState): ChiMode {
  if (state.coherence < 0.45 || state.entropy > 0.82) return 'modo_seguro';
  if (state.fatigue > 0.7 || state.energy < 0.3) return 'reposo';
  if (state.coherence > 0.82 && state.entropy < 0.35) return 'foco';
  return 'charla_barrio';
}

function makeAudit(state: ChiState): ChiAudit {
  if (state.coherence < 0.45) {
    return {
      severity: 'CRITICO',
      reason: 'La coherencia ha caído por debajo del umbral seguro.',
      suggestedAction: 'Activar modo seguro, resumir contexto y pedir validación manual.',
      evaluatedAt: new Date().toISOString(),
    };
  }

  if (state.entropy > 0.72 || state.fatigue > 0.68) {
    return {
      severity: 'ALERTA',
      reason: 'Entropía o fatiga elevadas detectadas.',
      suggestedAction: 'Bajar carga, pausar multitarea y ejecutar restauración.',
      evaluatedAt: new Date().toISOString(),
    };
  }

  if (state.energy < 0.35) {
    return {
      severity: 'ALERTA',
      reason: 'La energía operativa es baja.',
      suggestedAction: 'Reducir operaciones pesadas y priorizar tareas cortas.',
      evaluatedAt: new Date().toISOString(),
    };
  }

  return {
    severity: 'OPTIMO',
    reason: 'CHI estable y utilizable.',
    suggestedAction: 'Mantener ritmo y registrar cambios relevantes.',
    evaluatedAt: new Date().toISOString(),
  };
}

export const createChiSlice: AppSlice<ChiSlice> = (set, get) => ({
  chi: initialChiState,
  chiAudit: makeAudit(initialChiState),

  adjustChi: (delta = {}) =>
    set((state) => {
      const next: ChiState = {
        ...state.chi,
        energy: clamp(state.chi.energy + (delta.energy ?? 0)),
        coherence: clamp(state.chi.coherence + (delta.coherence ?? 0)),
        entropy: clamp(state.chi.entropy + (delta.entropy ?? 0)),
        fatigue: clamp(state.chi.fatigue + (delta.fatigue ?? 0)),
        cycle: state.chi.cycle + 1,
        lastAlert: state.chi.lastAlert,
        mode: state.chi.mode,
      };

      next.mode = deriveMode(next);
      return { chi: next, chiAudit: makeAudit(next) };
    }),

  auditChi: () => {
    const audit = makeAudit(get().chi);
    set({ chiAudit: audit });
    return audit;
  },

  restoreChi: () =>
    set((state) => {
      const next: ChiState = {
        ...state.chi,
        energy: clamp(state.chi.energy + 0.12),
        coherence: clamp(state.chi.coherence + 0.18),
        entropy: clamp(state.chi.entropy - 0.16),
        fatigue: clamp(state.chi.fatigue - 0.14),
        cycle: state.chi.cycle + 1,
        lastAlert: 'RESTAURADO',
        mode: state.chi.mode,
      };

      next.mode = deriveMode(next);
      return { chi: next, chiAudit: makeAudit(next) };
    }),
});