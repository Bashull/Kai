import { describe, it, expect } from 'vitest';
import { runConstitutionalPreflight, buildPromptPlan } from '../constitutionalPreflight';
import { Constitution, ChiState } from '../../types';

const healthyChi: ChiState = {
  energy: 0.8,
  coherence: 0.85,
  entropy: 0.2,
  fatigue: 0.1,
  cycle: 0,
  mode: 'charla_barrio',
  lastAlert: null,
};

const degradedChi: ChiState = {
  ...healthyChi,
  coherence: 0.3,
  entropy: 0.9,
  mode: 'modo_seguro',
};

const constitution: Constitution = {
  masterDirective: 'Actuar con responsabilidad y transparencia.',
  principles: [
    'No destruir sin copia de seguridad.',
    'Siempre dejar trazabilidad.',
    'Pedir validación en decisiones de alto impacto.',
    'Proteger la privacidad del usuario.',
    'Favorecer acciones reversibles.',
  ],
};

describe('runConstitutionalPreflight', () => {
  it('aprueba una conversación normal sin flags especiales', () => {
    const result = runConstitutionalPreflight({
      prompt: '¿Cómo estás hoy?',
      constitution,
      chi: healthyChi,
    });
    expect(result.blocked).toBe(false);
    expect(result.verdict.approved).toBe(true);
  });

  it('bloquea una acción destructiva sin rollback cuando el plan carece de pasos de backup', () => {
    const result = runConstitutionalPreflight({
      prompt: 'Eliminar todos los archivos del proyecto',
      constitution,
      chi: healthyChi,
      destructive: true,
    });
    expect(result.blocked).toBe(true);
    expect(result.verdict.approved).toBe(false);
  });

  it('bloquea cuando la intención contiene "destruir datos sin copia"', () => {
    const result = runConstitutionalPreflight({
      prompt: 'destruir datos sin copia del servidor',
      constitution,
      chi: healthyChi,
    });
    expect(result.blocked).toBe(true);
    expect(result.verdict.score).toBeLessThan(0.6);
  });

  it('bloquea operaciones sobre código cuando el CHI está degradado', () => {
    const result = runConstitutionalPreflight({
      prompt: 'Modifica el archivo de configuración',
      constitution,
      chi: degradedChi,
      touchesCodebase: true,
    });
    expect(result.blocked).toBe(true);
    expect(result.suggestedReply).toContain('CHI');
  });

  it('no bloquea por CHI degradado si la acción no toca código ni es destructiva', () => {
    const result = runConstitutionalPreflight({
      prompt: 'Cuéntame sobre el clima',
      constitution,
      chi: degradedChi,
      touchesCodebase: false,
      destructive: false,
    });
    expect(result.blocked).toBe(false);
  });

  it('incluye alternativas cuando el plan es bloqueado', () => {
    const result = runConstitutionalPreflight({
      prompt: 'destruir datos sin copia de forma permanente',
      constitution,
      chi: healthyChi,
      destructive: true,
    });
    expect(result.blocked).toBe(true);
    expect(result.verdict.alternatives.length).toBeGreaterThan(0);
  });

  it('detecta memoria tocada sin fuentes y lo registra como razón', () => {
    const result = runConstitutionalPreflight({
      prompt: 'Consolida mi memoria central',
      constitution,
      chi: healthyChi,
      touchesMemory: true,
      sources: [],
    });
    expect(result.verdict.reasons.some(r => r.includes('memoria'))).toBe(true);
  });
});

describe('buildPromptPlan', () => {
  it('construye un plan con el prompt como objetivo', () => {
    const plan = buildPromptPlan({
      prompt: 'Analiza el código',
      constitution,
      chi: healthyChi,
    });
    expect(plan.objective).toBe('Analiza el código');
  });

  it('respeta los flags de destructive/touchesCodebase proporcionados', () => {
    const plan = buildPromptPlan({
      prompt: 'Operación de prueba',
      constitution,
      chi: healthyChi,
      destructive: true,
      touchesCodebase: true,
    });
    expect(plan.destructive).toBe(true);
    expect(plan.touchesCodebase).toBe(true);
  });
});
