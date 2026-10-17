# PRODUCTION · Del cine al juego: modelo y controles independientes

No confundir trailer, escena cinemática, previs 3D y juego ejecutable. Compartir personaje/canon, rig compatible, materiales, locación, diálogos y ADR si su licencia lo permite; gameplay requiere además simulación y controles propios.

## Contrato de escena de juego
`engine/version`, target OS/renderer/hardware, frame budget y memoria, assets/LODs, input/feedback, collision layers, navegación, IA NPC, combate/mecánicas, estados de misión, persistencia/save/load, interfaces, accesibilidad y telemetría consentida. IDs de activo compartidos requieren conversión trazable USD→engine (escala, rotación, skeletal rigs, materiales, unidades).

## Testing profesional
- Godot: escenas de prueba, tests gdUnit4, ejecución headless (si está disponible), captura/replay de input + invariantes de estado.
- Unreal: automation tests, Gauntlet y Movie Render Queue según capacidades verificadas; no suponer que una secuencia Movie Render es un nivel jugable.
- O3DE: evaluación de engine modular y costes de mantenimiento.
- ML-Agents y behavior systems: NPC reactivos, con límites de seguridad e incertidumbre.
- GameCraft-Bench: patrones para ejecutar y puntuar juego mediante inputs y capturas; su dominio principalmente 2D **no prueba nivel AAA 3D**.

## Gates
`SOURCE_READY → BUILD_COMPILED → ENGINE_LAUNCHED → INPUT_REPLAYED → ASSERTIONS_OBSERVED → HUMAN_PLAYTESTED → PERFORMANCE_PROFILED → APPROVED`. No promocionar `BUILD_COMPILED` a `GAMEPLAY_VERIFIED`. Guardar hash build, trace, replay y entorno. Resultado estático de `director_gate.py` jamás reproduce el motor.
