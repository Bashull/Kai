---
name: kai-minecraft-cross-edition
description: Clasifica tareas de Minecraft Java, Bedrock o crossplay para Codex, identifica herramientas y limita la ejecución a planes sin efectos; úsala antes de operar una edición o servidor sin topología confirmada.
---

# Kai Minecraft — Router de ediciones (CANDIDATE)

**Estado:** READ_ONLY / dry-run / OFFLINE_TESTED / NOT_DEPLOYED. Este router no es un bot; nunca se conecta a Minecraft, instala plugins ni manipula mundos.

1. Recuperar primero el inventario del entorno real autorizado (edición, versión exacta, tipo de servidor, autenticación, mods, permisos y acceso al PC). Mientras sea desconocido, **solo descubrimiento**, no comandos.
2. Seleccionar la topología comprobada: `java` con `paper`, `spigot`, `fabric` o `forge`; `bedrock` con `bedrock-dedicated` o `powernukkitx`; `crossplay` exclusivamente si el host **Java** usa `geyser-java`. El puente Geyser no convierte Mineflayer en bot Bedrock nativo.
3. Crear un plan read-only: `python .agents/skills/kai-minecraft-cross-edition/scripts/route_mc.py --edition java --server paper --intent observe`.
   Con topología desconocida: `python .agents/skills/kai-minecraft-cross-edition/scripts/route_mc.py --edition unknown --server unknown --intent voice`.
   Para Bedrock nativo: `python .agents/skills/kai-minecraft-cross-edition/scripts/route_mc.py --edition bedrock --server bedrock-dedicated --intent observe`.
4. El resultado indica `adapter`, `dry_run_only=true`, `deployed=false`, `authorization=required_before_live_actions` y un siguiente gate. Nunca interpretar la salida como ejecución, conexión, compatibilidad probada ni consentimiento.
5. Ninguna skill generada puede ejecutar shell arbitrario, usar RCON remoto directo, desactivar autenticación, alterar el servidor Sóloland o lanzar cuentas no autorizadas. Mantener secretos en el vault del ordenador; registro sin valores confidenciales.
6. Si el host del servidor no coincide con la edición declarada, abortar. Si faltan versiones o dependencias, `unknown` y diagnóstico hasta obtener evidencia. Para clientes Bedrock en Java mediante Geyser, documentar las limitaciones y probar por separado.
7. Validación determinista: `python -m unittest discover -s tests -v`, `python .agents/skills/kai-minecraft-cross-edition/scripts/route_mc.py --edition unknown --server unknown --intent observe`. El adaptador de juego no se activará hasta pasar tests en staging y obtener aprobación del administrador.

**Fuentes de estudio:** `docs/minecraft/donor-ledger.json`, `docs/plans/2026-10-10-kai-minecraft-java-bedrock.md`. **Implementación:** `scripts/route_mc.py`. **Pruebas:** `tests/test_cross_edition.py`. **Racional:** GitHub `AIKUSAN/minecraft-agent-skills-bundle` (MIT) es donante de conceptos; el router es código original Kai y no copia sus scripts.
