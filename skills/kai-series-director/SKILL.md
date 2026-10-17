---
name: kai-series-director
description: Dirige y audita proyectos de series, cine, anime, live action y secuencias cinematográficas de videojuegos desde el canon y los contratos de KAI MEDIA FORGE OMEGA. Usar cuando se pidan guiones, episodios, storyboards, planificación de planos, producción virtual, tomas, continuidad, VFX, sonido, montaje, QC o adaptación interactiva. Carga referencias según la tarea; nunca afirma renderizado o QA real sin evidencia.
---

# KAI Series Director · extensión de investigación 0.4.1-MULTIHOST-CANDIDATE

**Estado:** CANDIDATE / VALIDATED_STATIC_SCOPE. Basada en la guía documental v0.3.1 del 16-10-2026 y en investigación audiovisual del 17-10-2026. **No es un merge demostrado del árbol Work `kai-series-director` (commit `ec3256ee…`)**. Se instala como portación compatible en Codex del PC, no altera el origen Work ni la autoridad del proyecto.

## Prioridades invariantes

1. **Recuperar CURRENT**: `KAI MEDIA FORGE OMEGA` es el paraguas; guía de director, biblia del proyecto, ShotPlan, ShotContinuity, MediaReferenceContract, ProductionCanonRegistry, Image/3D/Audio Forge, con alcance real. `KNOWN != UNDERSTOOD` y `NO LEÍDO != NO EXISTE`.
2. **Responsable creativo**: las cuatro funciones siguientes son roles lógicos del mismo director, no cuatro agentes con autoridad independiente. La aprobación editorial/humana se registra; una puntuación nunca invalida un HARD gate.
3. **Marchas proporcionales**: G1 escena/imagen/póster sencillo, G2 episodios o bloques, G3 serie/producción multidisciplinar. `requested_gear → minimum_gear → effective_gear`; módulos selectivos, no activar biomecánica para una canción.
4. **Fuentes por ámbito**: identidad canónica, estado narrativo, vista/apariencia y acción son dimensiones distintas. Una foto no permite deducir lo oculto. Identidad protegida no impide evolución aprobada explícita.
5. **Seguridad y economía**: secretos fuera de documentación. `SUBMIT_UNKNOWN` => consultar y reconciliar, nunca reenviar sin evidencia. Proveedor/modelo/licencia no puede autoautorizar pagos, publicidad, envío de datos biométricos, GPU remota ni publicación.
6. **Separar indicadores**: `CONTENT_REVIEWED`, `SCHEMA_VALID`, `PLAN_TESTED`, `RUNTIME_CONNECTED`, `MEDIA_DECODED`, `MEDIA_REVIEWED`, `GAMEPLAY_REPLAYED`, `APPROVED` y `PUBLISHED` son gates distintos. No heredar resultados entre ellos.

## Cuatro funciones de dirección (cargar solo las pertinentes)

- **STORY**: audiencia, motor de serie, bible, beats, setup/payoff, subtexto, guion y actor. Véase [narrativa y continuidad](references/01-story-canon-continuity.md).
- **VISUAL**: storyboard, blocking, actuación, continuidad espacial, cinematografía, anime 2D/3D y producción virtual. Véase [dirección audiovisual](references/02-visual-animation-and-virtual-production.md).
- **PRODUCTION**: activos, shots, estado, proveedores, créditos, derechos, publicación, USD/OTIO/OCIO y videojuegos. Véase [pipeline e interoperabilidad](references/03-pipeline-and-interchange.md) y [gaming](references/05-gameplay-and-interactive-cinematics.md).
- **QA/AUDIO**: audio y vídeo, artefactos, continuidad, selección de tomas, reparación localizada, mezcla, edición, revisión y master. Véase [posproducción](references/04-post-sound-and-delivery.md) y [loops](references/06-qa-loops-and-benchmarks.md).

## Flujo con recibos

`Brief + derechos → Biblia/estado CURRENT → guion → Episode/Scene/ShotIDs → Storyboard/Animatic → bloqueo de identidad/cámara/actuación → plan de activos → ejecución autorizada (servicio externo) → takes + hashes → QA separado → corte OTIO → conform y VFX → sonido → OCIO/ACES → master y distribución → archivo + genealogía.`

Los juegos reutilizan solo activos y canon compatibles. Después requieren además contratos **engine/inputs/colisiones/navmesh/interacción/NPC/render/performance/save/replay**. No traducir una cámara filmada directamente a controles de jugador.

## Evaluación local sin efectos secundarios

```bash
python scripts/director_gate.py fixtures/film_plan.json
python scripts/director_gate.py fixtures/hybrid_plan.json --out report.json
python -m unittest discover -s tests -v
```

El validador comprueba únicamente **contratos JSON declarados** (sin decodificación de imagen/audio, sin ejecución de motor, sin validación de copyright, sin inferencia ni gastos); sus `generation_authorized`, `media_decode`, `visual_review`, `audio_review`, `engine_execution` y `acceptance` no acreditan operaciones realizadas. Para elevar estado a `MEDIA_ACCEPTED` hacen falta herramientas de medios, revisión humana autenticada y evidencia verificable externa.

Schema del plan: `kai.director.plan/0.4-candidate`. `camera.exception.type='deliberate'` con `reason` y `evidence`; **NO** aceptar `axis_exception`. Separar `story_order`, `edit_order`, `production_order`; `asset_refs[]` deben resolver `id` y `state_version`. `source/license/rights_evidence` no equivale a clearance legal.

## Interoperabilidad con skills ya instaladas en Termux

Cuando esté disponible el catálogo local, cargar y reutilizar skills especializadas en vez de reimplementar sus funciones: `kai-image-forge-unified` para imágenes y su bloqueo de gasto cero, `independent-generative-qa-gates` para evaluación externa al generador, `multimedia-provider-benchmark` para comparación justa de modelos, `model-license-boundary-governance` para licencias de código/pesos/datasets y `repository-donor-extraction` para trasplantes con procedencia. Los nombres se observaron en Termux el 17-10-2026, sin asumir que existan en cualquier otro runtime. Véase [rutas existentes](references/09-existing-skill-routing.md).

## Control de adopción de donantes

Revisar siempre [registro de fuentes y ADN](references/07-donors-licenses-and-provenance.md). Cada nuevo código/modelo: identidad/commit, licencia, entradas/salidas, dependencias, límites GPU/OS, datos tratados, escenario de fallo, rollback, prueba sintética y comparación con CURRENT. Seguir REUSE → ADAPT → COMPOSE → ACQUIRE → BUILD. No importar código incompatible por recomendación documental.

## Regla de respuesta

Entregar plan y artefactos si se pidieron, más **estado factual de cada gate** (PASS/FAIL/NOT_RUN/UNKNOWN), bloqueos precisos y siguiente acción. En caso de falta de fuentes no inventar acceso, estado, resultado ni aprobación. Identificar claramente hipótesis y casos de muestra. No copiar secretos, API keys o embeddings de identidad al registro.

## Compatibilidad

`kai-series-director` Work v0.3.1: 15 guías / 99 tests **documentados** (no reejecutados aquí). Este pack: guías complementarias, validador `director_gate.py`, fixtures y pruebas propias. Lo correcto al recuperar el origen Work es hacer diff por contratos, ejecutar sus 99 pruebas y las nuevas, integrar por piezas y solo entonces promover versión unificada. [Instalación y recuperación](references/08-installation-recovery.md).
