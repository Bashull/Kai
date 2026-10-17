# STORY · Guion, biblia, estados y continuidad

1. Reconstruir premisa, género, audiencia, formato, duración, tono y motor repetible. Separar `SERIES_BIBLE/CANON` de solicitudes DRAFT y snapshots de episodio.
2. Mantener `WORLD_RULES`, `CHARACTER_DOSSIER`, `EPISODE_GRID`, `SCENE_LEDGER` y `SHOT_PLAN`. Para cada escena: objetivo, necesidad, obstáculo, táctica, subtexto, cambio observable, relación causal y hook.
3. Usar IDs persistentes `EP/SC/SH/TAKE` y genealogía de cambios. La revisión de un beat debe generar un `ChangeImpact` para planos, vestuario, sets, diálogos, música y activos afectados.
4. Dejar claro el tiempo diegético frente a orden de montaje y orden de producción. Un flashback consulta un snapshot anterior y no modifica el estado presente.
5. Sujetos: `IdentityLock` por época/revisión y referencias con autoridad por atributo; `SceneState` variable con causa y timestamps. Cosas ocultas `UNKNOWN`, no completarlas creativamente salvo permiso explícito.
6. Seguridad del personaje: contacto entre manos/props, lateralidad anatómica, número de dedos, escala, heridas, telas, suciedad, humedad y envejecimiento deben depender de una decisión canónica o de estado.
7. AI showrunner: los modelos pueden sugerir alternativas, detectar contradicciones y preparar versiones, pero **no** elevar DRAFT a CANON ni sustituir decisión creativa del usuario.

## Gates de revisión
- Narrativa: causalidad y consecuencias, setup/payoff, arco, subtexto, voz del personaje.
- Continuidad: entrada/salida, geografía, materiales, props, vestuario, información que conoce cada personaje.
- Texto: correspondencia de guion aprobado con diálogos y rótulos; timing solo medido con lectura o medios.
- Fuentes: planos aprobados no se deben reescribir por regeneración accidental.

## Donantes de estudio
CineCrew/FilmDSL, Dramatron, StoryMem, GroundShot. Son ideas y repositorios de estudio; ningún paper implica módulos instalados o probados. Un lenguaje intermedio de dirección se compara con ShotPlan y ShotContinuity antes de absorberse.
