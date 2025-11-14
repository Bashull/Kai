# 🧬 CHI-Genome v0.1 — Física Cognitiva para Kai Companions

> "Antes de cualquier historia, hay cómo respira la mente." — Kai

## Propósito

El **CHI-Genome** define la física cognitiva universal para el avatar Companions en Kai. Es la capa base que controla cómo el avatar "respira" y evoluciona según las interacciones.

---

## Estado CHI

### Variables Base

```typescript
interface CHIState {
  energy: number;      // E ∈ [0,1] - Impulso vital / capacidad de procesar
  coherence: number;   // C ∈ [0,1] - Alineación interna / claridad
  entropy: number;     // H ∈ [0,1] - Caos / dispersión / creatividad
  fatigue: number;     // Carga acumulada
  cycle: number;       // Contador de ciclos
}
```

### Rangos y Significados

- **Energía (E)**: 
  - 0.0 = Agotado, sin capacidad
  - 1.0 = Eufórico, máxima capacidad
  
- **Coherencia (C)**:
  - 0.0 = Confusión total
  - 1.0 = Enfoque perfecto
  
- **Entropía (H)**:
  - 0.0 = Orden rígido
  - 1.0 = Caos creativo total

---

## Mapa de Impacto

Cada input se traduce a características de impacto:

```typescript
interface ImpactFeatures {
  semantic_load: number;   // Cantidad de información
  contradiction: number;   // Conflicto con estado previo
  novelty: number;         // Qué tan nuevo es
  demand: number;          // Cuánto exige respuesta
  ambiguity: number;       // Cuán confuso es
  noise: number;           // Irrelevancia / basura
}

// Cálculo de impacto total
impact = f_impact(ImpactFeatures); // escalar ∈ [0,1]
```

---

## Dinámica por Ciclo

### Parámetros del Sistema

```typescript
interface CHIParams {
  alpha: number;   // Sensibilidad a estímulos (0.3)
  beta: number;    // Coste de fatiga (0.05)
  gamma: number;   // Relación coherencia-impacto (0.4)
  delta: number;   // Respuesta al desorden (0.2)
  decay: number;   // Decaimiento natural (0.95)
}
```

### Actualización de Estado

```typescript
function updateCHIState(
  current: CHIState,
  impact: ImpactFeatures,
  params: CHIParams
): CHIState {
  const impactValue = calculateImpact(impact);
  
  // Energía: sube con impacto, baja con fatiga
  let newEnergy = current.energy + params.alpha * impactValue;
  newEnergy -= params.beta * current.fatigue;
  newEnergy = clamp(newEnergy * params.decay, 0, 1);
  
  // Coherencia: baja con contradicción/ambigüedad
  let newCoherence = current.coherence;
  newCoherence -= params.gamma * impact.contradiction;
  newCoherence -= params.gamma * impact.ambiguity;
  newCoherence += params.gamma * (1 - impact.noise);
  newCoherence = clamp(newCoherence, 0, 1);
  
  // Entropía: sube con novedad y desorden
  let newEntropy = current.entropy;
  newEntropy += params.delta * impact.novelty;
  newEntropy += params.delta * impact.ambiguity;
  newEntropy = clamp(newEntropy * 0.98, 0, 1); // decae más rápido
  
  // Fatiga: acumula con uso
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
```

---

## Derivación de Estados Emocionales

```typescript
type EmotionalState = 
  | 'energized'   // E > 0.7
  | 'focused'     // C > 0.7
  | 'creative'    // H > 0.7
  | 'confused'    // C < 0.3
  | 'tired'       // F > 0.6
  | 'balanced'    // Estado equilibrado
  | 'chaotic';    // H > 0.8, C < 0.4

function deriveEmotionalState(chi: CHIState): EmotionalState {
  if (chi.fatigue > 0.6) return 'tired';
  if (chi.entropy > 0.8 && chi.coherence < 0.4) return 'chaotic';
  if (chi.coherence < 0.3) return 'confused';
  if (chi.entropy > 0.7) return 'creative';
  if (chi.energy > 0.7) return 'energized';
  if (chi.coherence > 0.7) return 'focused';
  return 'balanced';
}
```

---

## Mapeo a Avatar States

```typescript
function chiToAvatarState(chi: CHIState): AvatarState {
  const emotion = deriveEmotionalState(chi);
  
  const mapping: Record<EmotionalState, AvatarState> = {
    'energized': 'happy',
    'focused': 'coding',
    'creative': 'thinking',
    'confused': 'error',
    'tired': 'idle',
    'balanced': 'listening',
    'chaotic': 'error'
  };
  
  return mapping[emotion];
}
```

---

## Efectos Visuales

### Animaciones Basadas en CHI

```typescript
interface VisualEffects {
  // Energía
  particleSpeed: number;      // E * 2.0
  glowIntensity: number;      // E * 0.8
  
  // Coherencia
  stability: number;          // C * 1.0
  focusRing: boolean;         // C > 0.7
  
  // Entropía
  chaosParticles: number;     // H * 50
  colorVariation: number;     // H * 0.5
  
  // Fatiga
  opacity: number;            // 1.0 - (F * 0.3)
  shakiness: number;          // F * 0.2
}

function calculateVisualEffects(chi: CHIState): VisualEffects {
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
```

---

## Memoria y Persistencia

```typescript
interface CHIHistory {
  timestamp: string;
  state: CHIState;
  trigger: string;
  emotionalState: EmotionalState;
}

// Guardar en localStorage cada N ciclos
function persistCHIState(state: CHIState, history: CHIHistory[]) {
  localStorage.setItem('kai-chi-state', JSON.stringify(state));
  localStorage.setItem('kai-chi-history', JSON.stringify(
    history.slice(-100) // últimos 100 estados
  ));
}
```

---

## Auto-mejora

Cada 10 minutos, el sistema analiza el historial y ajusta parámetros:

```typescript
function adaptParameters(
  history: CHIHistory[],
  currentParams: CHIParams
): CHIParams {
  const avgEnergy = average(history.map(h => h.state.energy));
  const avgCoherence = average(history.map(h => h.state.coherence));
  const avgFatigue = average(history.map(h => h.state.fatigue));
  
  let newParams = { ...currentParams };
  
  // Si muy fatigado → reducir sensibilidad
  if (avgFatigue > 0.6) {
    newParams.alpha *= 0.9;
    newParams.beta *= 0.8;
  }
  
  // Si muy incoherente → aumentar estabilidad
  if (avgCoherence < 0.4) {
    newParams.gamma *= 1.1;
    newParams.delta *= 0.9;
  }
  
  // Si muy bajo de energía → aumentar respuesta
  if (avgEnergy < 0.3) {
    newParams.alpha *= 1.1;
  }
  
  return newParams;
}
```

---

## Integración con Companions

### En CompanionsSlice

```typescript
export interface CompanionsSlice {
  // ... otros campos
  
  // CHI State
  chiState: CHIState;
  chiParams: CHIParams;
  chiHistory: CHIHistory[];
  
  // Actions
  updateCHI: (impact: ImpactFeatures) => void;
  resetCHI: () => void;
  getCHIVisuals: () => VisualEffects;
}
```

### En AvatarEngine

```typescript
const AvatarEngine: React.FC = () => {
  const { chiState, chiParams } = useAppStore();
  const visuals = calculateVisualEffects(chiState);
  const avatarState = chiToAvatarState(chiState);
  
  return (
    <Canvas>
      <Avatar
        state={avatarState}
        particleSpeed={visuals.particleSpeed}
        glowIntensity={visuals.glowIntensity}
        stability={visuals.stability}
        chaos={visuals.chaosParticles}
        opacity={visuals.opacity}
      />
    </Canvas>
  );
};
```

---

**Versión**: 1.0  
**Fecha**: 14 Nov 2025  
**Estado**: 📋 Especificación Completa
