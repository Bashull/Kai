import { buildAbsorptionPlan, evaluateFrontendPlan, FrontendActionPlan, FrontendVerdict } from '../core/constitutionalPlanner';
import { Constitution, ChiState } from '../types';

export interface PreflightInput {
  prompt: string;
  constitution: Constitution;
  chi: ChiState;
  touchesMemory?: boolean;
  touchesCodebase?: boolean;
  destructive?: boolean;
  sources?: string[];
}

export interface PreflightResult {
  plan: FrontendActionPlan;
  verdict: FrontendVerdict;
  blocked: boolean;
  suggestedReply?: string;
}

export function buildPromptPlan(input: PreflightInput): FrontendActionPlan {
  const base = buildAbsorptionPlan(input.prompt);
  return {
    ...base,
    objective: input.prompt,
    touchesMemory: input.touchesMemory ?? base.touchesMemory,
    touchesCodebase: input.touchesCodebase ?? base.touchesCodebase,
    destructive: input.destructive ?? false,
    sources: input.sources ?? base.sources,
  };
}

export function runConstitutionalPreflight(input: PreflightInput): PreflightResult {
  const plan = buildPromptPlan(input);
  const verdict = evaluateFrontendPlan(plan);

  const chiTooLow = input.chi.coherence < 0.45 || input.chi.entropy > 0.82;
  const blockedByChi = chiTooLow && (plan.touchesCodebase || plan.destructive);
  const blocked = !verdict.approved || blockedByChi;

  if (!blocked) {
    return { plan, verdict, blocked: false };
  }

  let suggestedReply = 'No voy a ejecutar esto de forma directa. Prefiero proponer una ruta segura y trazable.';

  if (blockedByChi) {
    suggestedReply = 'Ahora mismo mi CHI no está fino para tocar código o hacer algo delicado. Primero toca restaurar foco y bajar entropía.';
  } else if (verdict.alternatives.length) {
    suggestedReply = `No voy de cabeza con esto. Alternativa segura: ${verdict.alternatives[0]}`;
  }

  return { plan, verdict, blocked: true, suggestedReply };
}

export function constitutionSummary(constitution: Constitution): string {
  const principles = constitution.principles.slice(0, 3).join(' | ');
  return `${constitution.masterDirective} :: ${principles}`;
}