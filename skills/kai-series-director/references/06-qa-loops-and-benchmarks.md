# QA · Loops de calidad, presupuestos y reparación localizada

Ciclo común: `especificar → preflight de derechos/refs → producir versión → observar → localizar fallo → reparar solo región/plano afectado → verificar vecinos → revisar → aprobar o retener`, con contador de intentos y salida de escalado humano.

| Loop | Entrada | Criterio visible | Acción si falla |
|---|---|---|---|
| Guion | beat/scene y canon | causalidad, objetivo, voz, setup/payoff | revisión autoral con ChangeImpact |
| Identidad | referencias/estado | rasgos protegidos visibles y correctos | reparar toma; evitar hallucination |
| Spatial | blocking, axis_id | continuidad de eje, miradas y orientación | corregir cámara/layout |
| Movimiento | contactos/timecode | posición mano/prop, pisada, física | ajustar pose/rig/frames |
| Audio | dialogue/cues/stems | voz, ritmo, lip sync y balance | ADR/alineación/mezcla |
| Edición | OTIO y vecinos | entradas/salidas, tiempo, raccord | retiming/conform |
| Color | OCIO/ACES transform | consistencia, clipping y gamuts | corregir transform/look |
| Proveedor | job id y receipt | idempotencia y estado de solicitud | SUBMIT_UNKNOWN: reconciliar |
| Juego | build y replay input | asserts de mundo, FPS y playtest | reparar nivel/mecánica |
| Publicación | hashes y destino | derechos, QC técnico y aprobación | retener release |

## Métricas
VBench/VBench2 o MSVBench son metodologías de investigación, no PASS automáticos. Segregar métricas de identidad, permanencia, acciones, geometría, habla y montaje. El benchmark necesita conjunto de referencia, implementación compatible, versiones de pesos, condiciones de ejecución y revisión humana. Un score agregado no anula un HARD gate.

## Policy de reintento
Por defecto `max_attempts=3` para una reparación localizada si el productor la autoriza; agotado => `ESCALATE_HUMAN`, no bucle eterno. No lanzar inferencia desde `director_gate`. La salida de esta CLI es **estática**, no inspecciona bytes del medio ni reproduce escenas. Ejes de evidencia por separado: hash, provenance, media decode, QA humana, consentimiento de identidad y legal.
