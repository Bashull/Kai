---
name: kai-minecraft-pc
description: Operar Minecraft Java desde un PC autorizado con Codex; diagnosticar cliente, mirar jugadores por RCON local y enviar mensajes o teclas limitadas con dry-run. Usar al pedir manejar Minecraft en el ordenador o conectar Codex con Minecraft.
---

# Kai Minecraft PC · operador candidato

**Estado:** CANDIDATE, pruebas aisladas; NO desplegado en PC ni conectado a Sóloland.

1. Antes de actuar, comprobar qué Minecraft se usa: Java o Bedrock, launcher, cliente activo, versión, tipo de servidor y permisos. No inferir que `mc.sololand.club:25565` ofrece RCON: 25565 es el puerto de juego, no RCON. No pedir ni almacenar contraseñas en el chat.
2. Estudiar CURRENT y genealogía: `SOLOLAND_PROJECT_MAP_CURRENT`, ancestro `Bashull/EntherEye-`, `Bashull/Kai`, ledger multimodal AI NPC de Drive. Reutilizar antes de crear.
3. Para ejecutar desde Codex en el PC, abrir el checkout de este repositorio. Lanzar `python .agents/skills/kai-minecraft-pc/scripts/mc_operator.py doctor`. No afirmar conectado porque el diagnóstico sea satisfactorio.
4. El script **no controla mundos Bedrock**. `players` y `say` usan RCON **solo** por `127.0.0.1` (también localhost/::1). Un RCON remoto requiere túnel cifrado ya establecido por un administrador, no publicar ni abrir el puerto RCON. La contraseña se resuelve en Hot Vault local y se inyecta como variable de entorno `KAI_MC_RCON_PASSWORD`, nunca se imprime, guarda o versiona.
5. Ejecutar primero `python .../mc_operator.py players` y `python .../mc_operator.py say 'Bienvenidos'` (dry-run). Sólo con autorización de administración y destinatarios, invocar `--apply`; `players --apply` observa y `say --apply` anuncia. En esta versión no hay comandos arbitrarios, cambios de bloques, permisos OP, TP, expulsiones ni acciones destructivas.
6. Para un **cliente Java abierto en primer plano**, instalar opcionalmente `pygetwindow` y `pyautogui` en entorno virtual del PC, con consentimiento. `python .../mc_operator.py screenshot C:\\ruta\\captura.png` hace dry-run. `--apply` captura pantalla al fichero indicado (privado); `key w --apply` pulsa una tecla permitida; `chat hola --apply` abre chat, escribe y envía. No actuar sin título activo Minecraft, ni con una ventana distinta, ni mientras el jugador use el teclado. `chat` es ASCII; jamás aceptar una cadena que empiece con `/` como comando. Cuidado con chat que otros jugadores verán. No usar esto para automatización continua sin supervisión.
7. **Pruebas y recuperación:** `python -m unittest discover -s tests -v`. El adaptador debe fallar cerrado ante credencial ausente, host remoto, ventana equivocada o teclas no permitidas. La recuperación es abortar la acción, nunca desactivar autenticación del servidor ni bajar barreras. Audit receipts distinguen plan/dry-run/acción/resultados; falta prueba end-to-end en PC.
8. La futura fase NPC (Citizens/Mineflayer/voz) requiere selección exacta de servidor, compatibilidad y copia de prueba. No dar permiso a una LLM para ejecutar comandos de administrador libres ni operar sobre producción de Sóloland hasta autorización específica.

Rutas: fuente `scripts/mc_operator.py`, pruebas repo `tests/`, documentación `docs/KAI_MINECRAFT_CODEX_RUNBOOK.md`. Fase siguiente: PC conectado → doctor → simulación de captura → captura real consentida → servidor de pruebas → RCON local con credenciales cargadas desde Hot Vault → observación y anuncio inocuo con recibos.
