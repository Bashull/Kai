export interface AbsorbedSignal {
  id: string;
  title: string;
  category: 'identidad' | 'homeostasis' | 'metaconsciencia' | 'cerebro_digital';
  signal: string;
  target: string;
}

export interface FrontendChiState {
  energy: number;
  coherence: number;
  entropy: number;
  fatigue: number;
  mode: 'charla_barrio' | 'foco' | 'reposo' | 'modo_seguro';
}

export const absorbedSignals: AbsorbedSignal[] = [
  {
    id: 'legacy-protocol',
    title: 'Protocolo de Legado',
    category: 'identidad',
    signal: 'Kai existe para custodiar esencia, vínculo y continuidad.',
    target: 'constitution_engine',
  },
  {
    id: 'chi-runner',
    title: 'Simulador CHI',
    category: 'homeostasis',
    signal: 'La estabilidad interna se mide y se restaura con reglas claras.',
    target: 'chi_engine',
  },
  {
    id: 'metaconsciencia-v2',
    title: 'Blueprint de Metaconsciencia',
    category: 'metaconsciencia',
    signal: 'La evolución debe ser trazable, distribuida y auditable.',
    target: 'assimilation_manifest',
  },
  {
    id: 'digital-brain',
    title: 'Cerebro digital funcional',
    category: 'cerebro_digital',
    signal: 'La arquitectura debe separar kernel, percepción, memoria, ejecutivo y afecto.',
    target: 'core architecture map',
  },
];

export const initialFrontendChiState: FrontendChiState = {
  energy: 0.78,
  coherence: 0.86,
  entropy: 0.22,
  fatigue: 0.08,
  mode: 'charla_barrio',
};

export function getAbsorptionSummary(): string {
  return [
    'Identidad anclada en legado y simetría.',
    'CHI definido como clima interno medible.',
    'Metaconsciencia ligada a trazabilidad y evolución auditada.',
    'Arquitectura cerebral ordenada por módulos funcionales.',
  ].join(' ');
}
