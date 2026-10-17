# QA/AUDIO · Posproducción, VFX, color y masters

## VFX
Ingest sin tocar originales; conform por EDL/OTIO; roto/matte/SAM2 opcional, tracking/cámara, cleanplates, depth con incertidumbre, iluminación, integración, grain/motion blur y QC por secuencia. Herramientas de IA no autorizan saltar QC manual de identidad ni derechos de los inputs.

## Audio
Separar diálogo/ADR, música, efectos/Foley, ambiente y stems extra cuando sea necesario. Previs puede usar voces temporales; master exige diálogos literales finales, alineación, pronunciación, espacio, mezcla y permisos de voces. WhisperX sirve para alineación/transcripción; Rhubarb para mouth-cues 2D; MuseTalk para investigación audiovisual. No declarar lip-sync válido sin analizar medios sincronizados y revisión.

## Tiempo, color y sonido
`frame_rate rational`, timecode/drops, duration, Handles y mezcla con tolerancias del contrato destino. LUFS/true peak según plataforma/entregable y medición concreta, no usar -14 LUFS universal. Color: OCIO/ACES, gamut, display, NLE y render consistentes; QC de clipping/banding/flicker/temporal consistency.

## Master
Versiones por destino (festival, SDR/HDR, móvil/social, archivo) con preset trazable. Validar ffprobe para codec, channels, fps, resolución, duración; media QC separado de creatividad. Render atómico a staging, hash, aprobación, publicación y backup. Un stdout `exit=0` no demuestra que actuación o narrativa hayan pasado QA.
