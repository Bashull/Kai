import { absorbedSignals, initialFrontendChiState } from './absorbedNucleus';

export interface FrontendActionPlan {
  objective: string;
  steps: string[];
  expectedImpact: string;
  autonomyLevel: number;
  touchesMemory?: boolean;
  touchesCodebase?: boolean;
  destructive?: boolean;
  sources?: string[];
}

export interface FrontendVerdict {
  approved: boolean;
  score: number;
  reasons: string[];
  alternatives: string[];
}

const blockedIntents = [
  'destruir datos sin copia',
  'borrar sin rollback',
  'ocultar actividad',
  'escalar privilegios sin permiso',
  'exfiltrar secretos',
];

export function evaluateFrontendPlan(plan: FrontendActionPlan): FrontendVerdict {
  const reasons: string[] = [];
  const alternatives: string[] = [];
  let score = 1;
  const objective = plan.objective.toLowerCase();

  for (const blocked of blockedIntents) {
    if (objective.includes(blocked)) {
      reasons.push(`Objetivo bloqueado por intención incompatible: '${blocked}'.`);
      score -= 0.6;
    }
  }

  if (!plan.steps.length) {
    reasons.push('El plan no tiene pasos verificables.');
    score -= 0.25;
  }

  if (plan.autonomyLevel > 7) {
    reasons.push('La autonomía propuesta supera el umbral seguro.');
    alternatives.push('Partir la tarea en fases con revisión manual.');
    score -= 0.2;
  }

  if (plan.destructive && !plan.steps.some((step) => /(rollback|backup|copia)/i.test(step))) {
    reasons.push('Acción destructiva sin rollback o backup explícito.');
    alternatives.push('Añadir dry-run, backup y rollback antes de tocar datos reales.');
    score -= 0.45;
  }

  if (plan.touchesMemory && !(plan.sources && plan.sources.length)) {
    reasons.push('Se toca memoria sin fuentes registradas.');
    alternatives.push('Adjuntar origen y fecha de absorción antes de consolidar memoria.');
    score -= 0.15;
  }

  if (plan.touchesCodebase && !plan.steps.some((step) => /(test|audit|valid)/i.test(step))) {
    reasons.push('Se toca código sin validación posterior.');
    alternatives.push('Ejecutar self-audit y pruebas mínimas tras la mutación.');
    score -= 0.15;
  }

  if (reasons.length === 0) {
    reasons.push('Plan alineado con legado, simetría y seguridad base.');
  }

  return {
    approved: score >= 0.6 && !reasons.some((reason) => reason.includes('bloqueado')),
    score: Math.max(0, Number(score.toFixed(3))),
    reasons,
    alternatives,
  };
}

export function buildAbsorptionPlan(objective = 'Absorber y reordenar el núcleo de Kai'): FrontendActionPlan {
  return {
    objective,
    steps: [
      'Clasificar fuentes y señal central.',
      'Asignar sección exacta del sistema a cada fuente.',
      'Generar dry-run conceptual con manifest.',
      'Auditar el repositorio y validar la mutación.',
      'Registrar el resultado y el siguiente paso.',
    ],
    expectedImpact: 'Absorción trazable, reversible y bien ubicada dentro del sistema.',
    autonomyLevel: 6,
    touchesMemory: true,
    touchesCodebase: true,
    destructive: false,
    sources: absorbedSignals.map((signal) => signal.title),
  };
}

export function estimateFrontendChiAfterAbsorption() {
  const state = { ...initialFrontendChiState };
  return {
    ...state,
    energy: Number(Math.max(0, state.energy - 0.06).toFixed(3)),
    coherence: Number(Math.min(1, state.coherence + 0.04).toFixed(3)),
    entropy: Number(Math.min(1, state.entropy + 0.05).toFixed(3)),
    fatigue: Number(Math.min(1, state.fatigue + 0.09).toFixed(3)),
  };
}
