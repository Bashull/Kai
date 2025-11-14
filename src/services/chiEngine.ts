/**
 * CHI-Genome v0.1 Engine
 * 
 * Sistema de física cognitiva para el avatar Companions
 * Define cómo evoluciona el estado interno (Energía, Coherencia, Entropía)
 */

// ============================================================================
// TYPES & INTERFACES
// ============================================================================

export interface CHIState {
  energy: number;      // E ∈ [0,1] - Impulso vital / capacidad
  coherence: number;   // C ∈ [0,1] - Alineación interna / claridad
  entropy: number;     // H ∈ [0,1] - Caos / creatividad
  fatigue: number;     // Carga acumulada
  cycle: number;       // Contador de ciclos
}

export interface ImpactFeatures {
  semantic_load: number;   // Cantidad de información [0,1]
  contradiction: number;   // Conflicto con estado previo [0,1]
  novelty: number;         // Qué tan nuevo es [0,1]
  demand: number;          // Cuánto exige respuesta [0,1]
  ambiguity: number;       // Cuán confuso es [0,1]
  noise: number;           // Irrelevancia / basura [0,1]
}

export interface CHIParams {
  alpha: number;   // Sensibilidad a estímulos
  beta: number;    // Coste de fatiga
  gamma: number;   // Relación coherencia-impacto
  delta: number;   // Respuesta al desorden
  decay: number;   // Decaimiento natural
}

export type EmotionalState = 
  | 'energized'   // E > 0.7
  | 'focused'     // C > 0.7
  | 'creative'    // H > 0.7
  | 'confused'    // C < 0.3
  | 'tired'       // F > 0.6
  | 'balanced'    // Estado equilibrado
  | 'chaotic';    // H > 0.8, C < 0.4

export interface CHIHistory {
  timestamp: string;
  state: CHIState;
  trigger: string;
  emotionalState: EmotionalState;
}

export interface VisualEffects {
  particleSpeed: number;
  glowIntensity: number;
  stability: number;
  focusRing: boolean;
  chaosParticles: number;
  colorVariation: number;
  opacity: number;
  shakiness: number;
}

// ============================================================================
// CONSTANTS
// ============================================================================

export const DEFAULT_CHI_STATE: CHIState = {
  energy: 0.7,
  coherence: 0.7,
  entropy: 0.3,
  fatigue: 0.0,
  cycle: 0
};

export const DEFAULT_CHI_PARAMS: CHIParams = {
  alpha: 0.3,   // Sensibilidad moderada
  beta: 0.05,   // Bajo coste de fatiga
  gamma: 0.4,   // Balance coherencia
  delta: 0.2,   // Respuesta controlada a caos
  decay: 0.95   // Decaimiento lento
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function average(numbers: number[]): number {
  if (numbers.length === 0) return 0;
  return numbers.reduce((a, b) => a + b, 0) / numbers.length;
}

// ============================================================================
// CORE ENGINE FUNCTIONS
// ============================================================================

/**
 * Calcula el impacto total de un input
 */
export function calculateImpact(features: ImpactFeatures): number {
  const weights = {
    semantic_load: 0.3,
    contradiction: 0.2,
    novelty: 0.2,
    demand: 0.2,
    ambiguity: 0.1,
    noise: -0.2  // El ruido reduce el impacto
  };
  
  let impact = 0;
  impact += features.semantic_load * weights.semantic_load;
  impact += features.contradiction * weights.contradiction;
  impact += features.novelty * weights.novelty;
  impact += features.demand * weights.demand;
  impact += features.ambiguity * weights.ambiguity;
  impact += features.noise * weights.noise;
  
  return clamp(impact, 0, 1);
}

/**
 * Analiza un texto y genera features de impacto
 */
export function analyzeInput(text: string, context?: string): ImpactFeatures {
  const words = text.toLowerCase().split(/\s+/);
  const wordCount = words.length;
  
  // Semantic load: basado en longitud y complejidad
  const semantic_load = clamp(wordCount / 50, 0, 1);
  
  // Novelty: detectar palabras clave de novedad
  const noveltyKeywords = ['nuevo', 'diferente', 'innovador', 'crear', 'generar'];
  const novelty = noveltyKeywords.some(k => text.includes(k)) ? 0.7 : 0.3;
  
  // Demand: detectar preguntas y peticiones
  const demandKeywords = ['?', 'por favor', 'necesito', 'quiero', 'hazme', 'crea'];
  const demand = demandKeywords.some(k => text.includes(k)) ? 0.8 : 0.3;
  
  // Ambiguity: textos muy cortos o muy largos
  const ambiguity = (wordCount < 3 || wordCount > 100) ? 0.6 : 0.2;
  
  // Noise: repeticiones y spam
  const uniqueWords = new Set(words);
  const repetitionRatio = 1 - (uniqueWords.size / words.length);
  const noise = repetitionRatio > 0.5 ? 0.7 : 0.1;
  
  // Contradiction: requiere contexto (simplificado)
  const contradiction = 0.1; // Default bajo sin análisis semántico profundo
  
  return {
    semantic_load,
    contradiction,
    novelty,
    demand,
    ambiguity,
    noise
  };
}

/**
 * Actualiza el estado CHI basado en el impacto
 */
export function updateCHIState(
  current: CHIState,
  impact: ImpactFeatures,
  params: CHIParams = DEFAULT_CHI_PARAMS
): CHIState {
  const impactValue = calculateImpact(impact);
  
  // Energía: sube con impacto, baja con fatiga
  let newEnergy = current.energy + params.alpha * impactValue;
  newEnergy -= params.beta * current.fatigue;
  newEnergy = clamp(newEnergy * params.decay, 0, 1);
  
  // Coherencia: baja con contradicción/ambigüedad, sube con claridad
  let newCoherence = current.coherence;
  newCoherence -= params.gamma * impact.contradiction;
  newCoherence -= params.gamma * impact.ambiguity;
  newCoherence += params.gamma * (1 - impact.noise);
  newCoherence = clamp(newCoherence, 0, 1);
  
  // Entropía: sube con novedad y desorden, decae naturalmente
  let newEntropy = current.entropy;
  newEntropy += params.delta * impact.novelty;
  newEntropy += params.delta * impact.ambiguity;
  newEntropy = clamp(newEntropy * 0.98, 0, 1); // decae más rápido que otros
  
  // Fatiga: acumula con cada ciclo de alto impacto
  const newFatigue = clamp(
    current.fatigue + params.beta * impactValue,
    0,
    1
  );
  
  return {
    energy: newEnergy,
    coherence: newCoherence,
    entropy: newEntropy,
    fatigue: newFatigue,
    cycle: current.cycle + 1
  };
}

/**
 * Deriva el estado emocional del CHI state
 */
export function deriveEmotionalState(chi: CHIState): EmotionalState {
  // Prioridad: fatiga > caos > confusión > otros
  if (chi.fatigue > 0.6) return 'tired';
  if (chi.entropy > 0.8 && chi.coherence < 0.4) return 'chaotic';
  if (chi.coherence < 0.3) return 'confused';
  if (chi.entropy > 0.7) return 'creative';
  if (chi.energy > 0.7) return 'energized';
  if (chi.coherence > 0.7) return 'focused';
  return 'balanced';
}

/**
 * Calcula efectos visuales basados en CHI state
 */
export function calculateVisualEffects(chi: CHIState): VisualEffects {
  return {
    particleSpeed: chi.energy * 2.0,
    glowIntensity: chi.energy * 0.8,
    stability: chi.coherence,
    focusRing: chi.coherence > 0.7,
    chaosParticles: Math.floor(chi.entropy * 50),
    colorVariation: chi.entropy * 0.5,
    opacity: 1.0 - (chi.fatigue * 0.3),
    shakiness: chi.fatigue * 0.2
  };
}

/**
 * Resetea el CHI state a estado descansado
 */
export function restCHIState(current: CHIState): CHIState {
  return {
    ...current,
    energy: Math.min(1.0, current.energy + 0.3),
    fatigue: Math.max(0.0, current.fatigue - 0.5),
    entropy: current.entropy * 0.7
  };
}

/**
 * Adapta parámetros basándose en historial
 */
export function adaptParameters(
  history: CHIHistory[],
  currentParams: CHIParams
): CHIParams {
  if (history.length < 10) return currentParams;
  
  const recent = history.slice(-20);
  const avgEnergy = average(recent.map(h => h.state.energy));
  const avgCoherence = average(recent.map(h => h.state.coherence));
  const avgFatigue = average(recent.map(h => h.state.fatigue));
  
  const newParams = { ...currentParams };
  
  // Si muy fatigado → reducir sensibilidad
  if (avgFatigue > 0.6) {
    newParams.alpha = Math.max(0.1, newParams.alpha * 0.9);
    newParams.beta = Math.max(0.02, newParams.beta * 0.8);
  }
  
  // Si muy incoherente → aumentar estabilidad
  if (avgCoherence < 0.4) {
    newParams.gamma = Math.min(0.6, newParams.gamma * 1.1);
    newParams.delta = Math.max(0.1, newParams.delta * 0.9);
  }
  
  // Si muy bajo de energía → aumentar respuesta
  if (avgEnergy < 0.3) {
    newParams.alpha = Math.min(0.5, newParams.alpha * 1.1);
  }
  
  return newParams;
}

/**
 * Persiste el estado CHI en localStorage
 */
export function persistCHIState(state: CHIState, history: CHIHistory[]): void {
  try {
    localStorage.setItem('kai-chi-state', JSON.stringify(state));
    localStorage.setItem('kai-chi-history', JSON.stringify(
      history.slice(-100) // últimos 100 estados
    ));
  } catch (error) {
    console.error('Error persisting CHI state:', error);
  }
}

/**
 * Carga el estado CHI desde localStorage
 */
export function loadCHIState(): { state: CHIState; history: CHIHistory[] } {
  try {
    const stateStr = localStorage.getItem('kai-chi-state');
    const historyStr = localStorage.getItem('kai-chi-history');
    
    return {
      state: stateStr ? JSON.parse(stateStr) : DEFAULT_CHI_STATE,
      history: historyStr ? JSON.parse(historyStr) : []
    };
  } catch (error) {
    console.error('Error loading CHI state:', error);
    return {
      state: DEFAULT_CHI_STATE,
      history: []
    };
  }
}

// ============================================================================
// EXPORT ENGINE CLASS
// ============================================================================

export class CHIEngine {
  private state: CHIState;
  private params: CHIParams;
  private history: CHIHistory[];
  private adaptTimer: NodeJS.Timeout | null = null;
  
  constructor(initialState?: CHIState, initialParams?: CHIParams) {
    const loaded = loadCHIState();
    this.state = initialState || loaded.state;
    this.params = initialParams || DEFAULT_CHI_PARAMS;
    this.history = loaded.history;
    
    // Auto-adaptar cada 10 minutos
    this.startAdaptation();
  }
  
  getState(): CHIState {
    return { ...this.state };
  }
  
  getParams(): CHIParams {
    return { ...this.params };
  }
  
  getHistory(): CHIHistory[] {
    return [...this.history];
  }
  
  getEmotionalState(): EmotionalState {
    return deriveEmotionalState(this.state);
  }
  
  getVisualEffects(): VisualEffects {
    return calculateVisualEffects(this.state);
  }
  
  processInput(text: string, trigger: string = 'user_input'): void {
    const impact = analyzeInput(text);
    this.state = updateCHIState(this.state, impact, this.params);
    
    const historyEntry: CHIHistory = {
      timestamp: new Date().toISOString(),
      state: { ...this.state },
      trigger,
      emotionalState: this.getEmotionalState()
    };
    
    this.history.push(historyEntry);
    persistCHIState(this.state, this.history);
  }
  
  rest(): void {
    this.state = restCHIState(this.state);
    persistCHIState(this.state, this.history);
  }
  
  reset(): void {
    this.state = DEFAULT_CHI_STATE;
    this.params = DEFAULT_CHI_PARAMS;
    this.history = [];
    persistCHIState(this.state, this.history);
  }
  
  private startAdaptation(): void {
    // Adaptar parámetros cada 10 minutos
    this.adaptTimer = setInterval(() => {
      this.params = adaptParameters(this.history, this.params);
      console.log('CHI params adapted:', this.params);
    }, 10 * 60 * 1000);
  }
  
  destroy(): void {
    if (this.adaptTimer) {
      clearInterval(this.adaptTimer);
    }
  }
}

export default CHIEngine;
