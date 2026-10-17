# PRODUCTION · Pipeline, versiones y normas de intercambio

## Authorities (nunca duplicar)
- KAI MEDIA FORGE OMEGA: dirección y producción; KAI Visual Production Pipeline: jobs/receipts.
- ProductionCanonRegistry/ShotContinuity/MediaReferenceContract: identidad, estado, shot planning y referencias bajo su vigencia real.
- GitHub: fuente versionada y tests. Drive: canon/documentos/decisiones/evidencias. Workspace PC/Termux: staging/runtime. Proveedores no son fuentes de verdad.

## AYON/Kitsu/Zou
Extraer taxonomía `Project/Sequence/Shot/Asset/Task/Version/Review/Publish`, validadores en publicación y bloqueo de assets no aprobados. No instalar bases de datos duplicadas: primero comparar modelos con Omega/Fusion v0.7. Publicar salidas inmutables y puntero a selección aprobada. Dailies/reviews deben tener usuario, nota, fecha y receipt.

## USD / OTIO / OCIO
- OpenUSD: composición de escenas 3D, referencias, variantes y formato de intercambio; no codifica decisiones editoriales de vídeo de manera automática.
- OpenTimelineIO: cortes, clips, rangos, transiciones y sus adapters; `OTIO != render ejecutado`. Conform con FFmpeg o NLE sobre medios verificados.
- OpenColorIO/ACES: controlar espacio de entrada, display/view transforms, rango dinámico, referencia SDR/HDR y salida por plataforma. No usar LUT arbitraria como contrato global.
- MaterialX/OpenEXR: materiales e intercambio de información de render; probar compatibilidad entre versiones.
- OpenCue: cola/batch render, workers, recursos y reintentos; presupuestos y deadlines explícitos.

## Entregables de producción
Manifest con hash SHA256, tamaño, origen, licencia, autorización, revisión, escena/plano/take, hardware/perfil, dependencias, tiempo de salida, logs redactados y políticas de privacidad. Cache/thumbs regenerables; no sobrescribir fuentes sin respaldo/rollback.

## Compilación a providers
Compilador neutral: `ShotSpec → References (allowlist) → constraints HARD/SOFT → provider capability check → cost/privacy authorization → submit with idempotency key → poll/cancel/reconcile → safe ingest → TakeCandidate → QA`. `SUBMIT_UNKNOWN` no retransmitir. Fallo externo, cuota y core local son estados distintos.
