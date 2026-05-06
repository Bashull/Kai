# Q_CHI_CANON_v1

**proyecto:** FusionAI / KaiOS  
**módulo:** Q-CHI Motor  
**versión:** 1.0  
**fecha:** 2026-05-06  
**estado:** aprobado v0.3  
**decisiones de referencia:** DEC-2026-05-05-QCHI-001 a QCHI-004

---

## Principio raíz

```
CHI y Quantum no se fusionan en una sola variable.
Se acoplan de forma jerárquica.
```

```
CHI           = salud del organismo
Quantum       = variación permitida por esa salud
Pituitaria    = modulador del clima
Voto          = decisión
Huella Entrópica = certificación
```

**Prohibido:**  
`Quantum-CHI = una sola magnitud mezclada`

Motivo: pierde trazabilidad, confunde ruido con creatividad, impide diagnóstico.

---

## Variables CHI

| Variable  | Significado                                          |
|-----------|------------------------------------------------------|
| energy    | combustible operativo disponible                     |
| coherence | alineación con identidad, memoria, canon, continuidad|
| entropy   | desorden, ruido estructural, deriva                  |
| fatigue   | desgaste acumulado                                   |
| cycle     | número de ciclo metabólico                           |
| mode      | estado operativo derivado                            |

## Umbrales canónicos

```python
DEFAULT_ENERGY    = 0.78
DEFAULT_COHERENCE = 0.86
DEFAULT_ENTROPY   = 0.22
DEFAULT_FATIGUE   = 0.08

COHERENCE_CRITICAL = 0.45    # fuerza modo_seguro
COHERENCE_FOCUS    = 0.82    # umbral para modo foco

ENERGY_ALERT  = 0.35
ENERGY_REST   = 0.30

ENTROPY_ALERT     = 0.72
ENTROPY_SAFE_MODE = 0.82     # fuerza restauración
ENTROPY_FOCUS     = 0.35

FATIGUE_ALERT = 0.68
FATIGUE_REST  = 0.70
```

---

## Modos Q-CHI

| Modo          | Descripción                                  |
|---------------|----------------------------------------------|
| charla_barrio | naturalidad, cercanía, chispa controlada     |
| foco          | precisión, baja variación, alta coherencia   |
| reposo        | baja carga, conservación                     |
| modo_seguro   | integridad antes que producción              |
| forja         | exploración controlada                       |
| restauracion  | reanclaje, quantum nulo o casi nulo          |

---

## Quantum Variation Layer

**Quantum puede entrar en:**
- desempates
- flexibilidad de estilo
- creatividad verbal moderada
- exploración en forja
- selección entre rutas equivalentes
- anti-respuesta clonada
- asociaciones no obvias

**No puede tocar:**
- identidad
- hechos nucleares
- memoria sagrada
- decisiones de seguridad
- restauración / modo seguro
- vetos éticos

> Quantum colorea. No gobierna.

## Caps por modo

| Modo          | Cap quantum |
|---------------|-------------|
| charla_barrio | 0.06        |
| foco          | 0.02        |
| reposo        | 0.015       |
| modo_seguro   | 0.01        |
| forja         | 0.08        |
| restauracion  | 0.00        |

---

## PituitaryModulator

**Entradas:** CHIState · mode · context_bias · quantum_seed

**Salidas:** quantum_variation · creative_aperture · mood_state · vote_modulation · risk_tolerance

**Fórmula de apertura creativa:**
```
creative_aperture =
  0.15
  + energy    * 0.25
  + coherence * 0.20
  - entropy   * 0.30
  - fatigue   * 0.20
```

> La Pituitaria no inventa verdad.  
> Ajusta el clima de decisión.

> operational_noise y quantum_variation no se mezclan.  
> operational_noise ensucia. quantum_variation vivifica.

---

## NhipTheVote

**Fórmulas canónicas:**
```
confidence       = perception × (1 + reflection)

state_stability  = (coherence + energy + (1 - entropy) + (1 - fatigue)) / 4

weighted_score   = confidence × state_stability × vote_modulation − risk_penalty
```

**Reglas:**
- El voto gana por calidad, no por ruido.
- El quantum solo modula un poco.
- Si hay empate serio, conflicto o identidad sensible, se eleva a Corona.

---

## EntropicFingerprint

Certifica cada decisión importante con:
- timestamp · mode · chi_state · pituitary_state
- nuclei_called · votes · final_output
- **hash SHA-256** del payload completo

> No es logging decorativo.  
> Es trazabilidad cognitiva.

---

## Flujo Q-CHI canon

```
input
→ CHIEngine.adjust(operational_noise=...)
→ CHIEngine.audit()
→ si CRÍTICO: restore() / modo_seguro / Corona
→ PituitaryModulator.build_state(chi=...)
→ NhipTheVote.resolve(votes, chi=..., pituitary=...)
→ EntropicFingerprintBuilder.build(...)
→ output estructurado
```

## Árbol del módulo

```
core/brain/q_chi/
├── __init__.py
├── constants.py
├── schemas.py
├── chi_engine.py
├── pituitary_modulator.py
├── nhip_the_vote.py
├── entropic_fingerprint.py
└── q_chi_runtime.py
```

## API FastAPI

| Método | Endpoint           | Descripción                     |
|--------|--------------------|---------------------------------|
| GET    | /api/qchi/state    | Estado CHI actual               |
| POST   | /api/qchi/restore  | Restauración suave del CHI      |
| POST   | /api/qchi/process  | Ciclo completo Q-CHI            |
