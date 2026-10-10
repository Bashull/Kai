<!-- Master document: https://docs.google.com/document/d/1VEsO8l2OHLux66vUx45Cd44uzR1r80PTW1KQJf1xJ8o/edit?usp=drivesdk -->
<!-- This GitHub plan is an executable code-adjacent snapshot, not the documentary CURRENT -->

# KAI Minecraft Java + Bedrock Implementation Plan

> **For agentic workers:** Execute tasks one by one with the available implementation workflow. Use - [ ] for tracking; evidence before promotion.

**Goal:** Preparar a Codex para aprender, diagnosticar y finalmente operar de forma supervisada Minecraft Java y Bedrock desde el PC de Asier, evolucionando a Kai como NPC/comentarista sin modificar Sóloland sin autorización.

**Architecture:** Control plane común con contratos de capacidades, política explícita, registro de evidencia y memoria; adaptadores independientes Java/Bedrock; capa de skill-router para Codex; evento -> narración -> voz opcional. Nada de LLM -> comandos arbitrarios ni de proxy de autenticación desactivada. Mantener el checkout de producción y servidores reales intactos.

**Tech Stack:** Python 3.10+ (núcleo/skills), Node.js/TypeScript (Mineflayer, bedrock-protocol, MCP), PowerShell/Termux/Remote Desktop Commander para diagnóstico autorizado, Java/Paper/Fabric sólo si el tipo de servidor lo permite, Bedrock Script API/PocketMine sólo para entornos compatibles, GitHub + Drive.

## Global Constraints
- La edición, versión, launcher, servidor y permisos de Sóloland siguen SIN VERIFICAR. mc.sololand.club:25565 es dirección del juego, no un RCON conocido.
- Todo en rama o workspace aislado; no tocar producción, no reset de checkouts con cambios, no migrar mundos, ni alterar online-mode; pruebas reproducibles y rollback.
- GitHub = código; Google Drive = planificación, canon, genealogía, checkpoints; no mezclar documentación histórica con runtime probado.
- SECRETOS fuera de GitHub, Drive, logs y prompts; vault local con referencias, RCON sólo por loopback/túnel cifrado y acciones allowlisted.
- Código de Minecraft propietario: estudiar localmente con herramientas y condiciones de Mojang, sin republicar fuentes ni assets extraídos.
- Código externo: registrar licencia y commit exacto antes de reutilizar. NetherGames plugins AGPL-3.0; assets CC BY 4.0 con atribución; no hacer copia directa al código Kai sin revisión legal.
- No borrar ni perder material: manifest SHA-256, URL, commit, licencia, función, duplicados y dependencia; backups verificables antes de modificar.
- NO asumir que un Java bot se vuelve Bedrock por usar Geyser: el proxy permite entrar a un servidor Java desde Bedrock; Bedrock nativo necesita contrato propio.
- Estados separados: SOURCE_FOUND / DOCUMENTED / TESTED_OFFLINE / TESTED_LOCAL / TESTED_STAGING / DEPLOYED. Actualmente NO DEPLOYED.

---

## INVENTARIO DE DONANTES — verificado por repositorios y documentación a 2026-10-10

| Prioridad | Fuente | Edición / papel | Licencia observada | Disposición |
| --- | --- | --- | --- | --- |
| P0 | https://github.com/Bashull/Kai rama feat/codex-minecraft-pc-20261010 | tres skills Codex, operador GUI/RCON y comentarista | propio; conservar | autoridad de código del nuevo trabajo |
| P0 | https://github.com/Bashull/EntherEye- | prototipo histórico Java/Bedrock, sin NPC funcional; translator no presente | comprobar fichero por fichero | DONOR histórico; NUNCA ejecutar configuración insegura |
| P0 | https://github.com/AIKUSAN/minecraft-agent-skills-bundle | router y skills Java/Bedrock, bot QA | MIT | ESTUDIAR contratos/pruebas, no instalar ciegamente |
| P0 | https://github.com/PrismarineJS/mineflayer | bot cliente Java | MIT | candidato adaptador Java |
| P0 | https://github.com/yuniko-software/minecraft-mcp-server | MCP para operar bot Java usando Mineflayer | Apache-2.0 | candidato a conectar Codex |
| P0 | https://github.com/PrismarineJS/bedrock-protocol | protocolo para cliente Bedrock | MIT | candidato adaptador Bedrock; autenticación y versión deben probarse |
| P0 | https://github.com/microsoft/minecraft-scripting-samples | Script API/GameTest Bedrock | MIT (repo) | pruebas oficial-like en mundo de desarrollo |
| P0 | https://learn.microsoft.com/en-us/minecraft/creator/scriptapi/?view=minecraft-bedrock-stable | referencia oficial módulos de Bedrock | documentación de Microsoft | contrato de Bedrock por versión |
| P1 | https://github.com/Mojang/bedrock-samples | assets y ejemplos Bedrock, con licencia propia | inspeccionar LICENSE antes de copiar | fuente oficial de estudio, no licencia libre global inferida |
| P1 | https://github.com/Mojang/minecraft-scripting-libraries | utilidades TypeScript para scripting | MIT | posibles utilidades, no copiar sin relevancia |
| P1 | https://github.com/GeyserMC/Geyser | Bedrock -> Java crossplay | MIT | sólo si Sóloland es servidor Java y el diseño lo requiere |
| P1 | https://github.com/GeyserMC/Floodgate | autenticación para Geyser | MIT | evaluar instalación y seguridad por admin |
| P1 | https://github.com/CloudburstMC/Protocol | biblioteca Java del protocolo Bedrock | Apache-2.0 | alternativa de bajo nivel, no duplicar adaptador JS innecesariamente |
| P1 | https://github.com/NetherGamesMC/plugins | Bedrock/PocketMine: Duels, libminigames | AGPL-3.0 | estudiar estados, equipos, colas, puntuación, premios; licencia como gate |
| P1 | https://github.com/NetherGamesMC/assets | arenas/mapas/configs Bedrock | CC BY 4.0 (LICENSE del repo) | estudiar diseño; atribución si se usan materiales |
| P1 | https://github.com/mindcraft-bots/mindcraft | agente LLM + Mineflayer Java | MIT | estudiar bucle pensamiento/herramientas, NUNCA ejecución libre de código |
| P1 | https://github.com/MineDojo/Voyager | biblioteca de skills/recuperación de agente | MIT | donor cognitivo, menos reciente, no runtime de producción |
| P1 | https://github.com/CraftJarvis/MineStudio | infraestructura de investigación agentes Minecraft | MIT | candidato entorno de pruebas/benchmark |
| P2 | https://github.com/nexxii04/minecraft-bedrock-mcp | prueba independiente de bot Bedrock/MCP | LICENCIA NO VERIFICADA | estudiar interfaz/tests; NO copiar |
| P2 | https://github.com/Bram1903/MinecraftSourcesGenerator | generador local de fuentes Java vanilla | LICENCIA HERRAMIENTA NO VERIFICADA | estudiar localmente la versión exacta; jamás subir fuentes generadas |
| P2 | https://github.com/TheDarkSword/mc-vanilla-src | scripts de estudio de vanilla Java | condiciones a revisar | herramienta de estudio, no repositorio oficial de código Mojang |
| P2 | https://github.com/luanti-org/luanti y https://github.com/VoxeLibre/VoxeLibre | motor voxel y juego abierto ANÁLOGO, NO Minecraft | revisar archivos por componente (VoxeLibre GPL-3.0) | aprender implementación de chunks, física, inventario sin confundir producto |
| P2 | https://github.com/henkelmax/simple-voice-chat | voz por proximidad (Java) | verificar por módulos | posible canal posterior, dependiente de compatibilidad |

Fuentes comunitarias: https://www.reddit.com/r/admincraft/comments/1fxvoz4 y https://www.reddit.com/r/admincraft/comments/1flvwrw advierten de limitaciones con mods cliente y GUI/clics Bedrock en servidores Java con Geyser. Son experiencias, NO pruebas universales.

## FASES Y GATES — sin instalación automática en Sóloland

### Task 0: Congelar baseline y genealogía — INICIADO (inventario conectado leído)
**Files:**
- Existing: .agents/skills/kai-minecraft-pc/SKILL.md; .agents/skills/kai-minecraft-skill-forge/SKILL.md; .agents/skills/kai-sololand-commentator/SKILL.md; docs/KAI_MINECRAFT_CODEX_RUNBOOK.md; tests/test_skills.py
- Proposed: docs/minecraft/donor-ledger.json; docs/minecraft/source-license-report.md
**Interfaces:**
- Consumes: GitHub URL + immutable commit hash + licencia + función técnica.
- Produces: donor manifest con id, repositorio, ref, licencia, señales mantenimiento y permiso COPY/STUDY_ONLY/BLOCKED.
- [ ] **Step 1 (test rojo):** escribir tests/test_donor_ledger.py que falle si falta commit, estado de licencia o procedencia.
- [ ] **Step 2:** ejecutar python -m unittest tests.test_donor_ledger -v; registrar error esperado.
- [ ] **Step 3:** implementar manifiesto reproducible, etiquetar licencias ambiguas BLOCKED_FOR_COPY y excluir código propietario.
- [ ] **Step 4:** repetir test hasta PASS.
- [ ] **Step 5:** comprobar que los nueve archivos de la rama baseline siguen intactos y registrar SHA-256; distinguir 10 tests versionados de suites locales extra que no estén en Git.
- [ ] **Step 6:** commit sólo tras pruebas. No descargar assets grandes automáticamente.

### Task 1: Descubrimiento de entorno PC + capacidades — bloqueado por PC OFFLINE
**Files:**
- Modify: .agents/skills/kai-minecraft-pc/scripts/mc_operator.py (solo si test detecta necesidad)
- Proposed: .agents/skills/kai-minecraft-pc/scripts/pc_inventory.py; tests/test_pc_inventory.py
**Interfaces:**
- Consumes: ordenador autorizado, rutas locales y procesos; NO secretos.
- Produces: minecraft_environment.json con OS, versión Python/Node/Java, ediciones instaladas, cliente activo, puertos locales observados y rutas REDACTED de credenciales.
- [ ] **Step 1 (rojo):** tests sintéticos comprueban selección Java/Bedrock, ausencia cliente y puertos no asumidos.
- [ ] **Step 2:** ejecutar python -m unittest tests.test_pc_inventory -v => falla función inexistente.
- [ ] **Step 3:** crear inventario read-only; no instalar, no abrir puertos, no leer tokens.
- [ ] **Step 4:** PASS casos Java-only, Bedrock-only, ambos, ninguno.
- [ ] **Step 5:** en PC autorizado: doctor; informe solo lectura; comparar permisos contra consola real.
- [ ] **Step 6:** checkpoint y commit. Gate: edición+versión+API objetivo verificados.

### Task 2: Router Codex y contratos de permisos
**Files:**
- Proposed: .agents/skills/kai-minecraft-task-router/SKILL.md; .agents/skills/kai-minecraft-task-router/scripts/route_task.py; tests/test_task_router.py
**Interfaces:**
- Consumes: request {edition, intent, target, impact, approval, environment}.
- Produces: plan {adapter, action, dry_run, required_approvals, rollback_strategy} o rechazo explícito.
- [ ] **Step 1 (rojo):** tests exigen Java→JAVA, Bedrock→BEDROCK, edición ambigua→STOP_AND_DISCOVER, acciones mutadoras sin aprobación→DENIED.
- [ ] **Step 2:** python -m unittest tests.test_task_router -v => fallos de ruta aún no definida.
- [ ] **Step 3:** tabla estática de capacidades. No permitir shell/JS arbitrario ni comandos admin pasados por LLM.
- [ ] **Step 4:** PASS y recibos auditables con correlation_id.
- [ ] **Step 5:** python -m unittest discover -s tests -v sin regresiones en scripts actuales.
- [ ] **Step 6:** commit aislado. Gate: permisos fail-closed y reproducibilidad.

### Task 3: Adaptador Java de SOLO LECTURA y bot de pruebas
**Files:**
- Proposed: .agents/skills/kai-minecraft-java/SKILL.md; adapters/java/client.ts; adapters/java/events.ts; tests/java/adapter.test.ts
**Interfaces:**
- Consumes: host staging, versión protocol, cuenta de prueba autenticada, allowlist.
- Produces: {players, bot_status, position, nearby_entities, health} y eventos normalizados; NO escritura hasta nuevo gate.
- [ ] **Step 1 (rojo):** tests mock Mineflayer para connect/status/disconnect, auth fallida, timeout, reconexión limitada, server de producción negado.
- [ ] **Step 2:** node --test tests/java/adapter.test.ts o test runner fijado en package.json del módulo.
- [ ] **Step 3:** adaptar Mineflayer/MCP con acciones observacionales sin añadir cliente en mundo real.
- [ ] **Step 4:** tests unitarios PASS; validar versiones con lockfile.
- [ ] **Step 5:** staging privado con bot y credenciales de prueba, sin desactivar online-mode.
- [ ] **Step 6:** commit. Gate: un evento de mundo leído de forma verificable.

### Task 4: Adaptador Bedrock independiente
**Files:**
- Proposed: .agents/skills/kai-minecraft-bedrock/SKILL.md; adapters/bedrock/client.ts; adapters/bedrock/script-events.ts; tests/bedrock/adapter.test.ts
**Interfaces:**
- Consumes: endpoint Bedrock de pruebas, auth/protocol soportados o @minecraft/server Script API en entorno autorizado.
- Produces: esquema normalizado compartido {edition, event_type, entity_id, tick, payload, source_id}; NO ejecutar comandos admins.
- [ ] **Step 1 (rojo):** tests con mock bedrock-protocol y fixtures oficiales para auth/version mismatch/reconnect/event schema; sin dependencia de Java.
- [ ] **Step 2:** node --test tests/bedrock/adapter.test.ts => falla contrato inexistente.
- [ ] **Step 3:** implementar mínimo receptor no mutador; usar docs Script API y biblioteca de protocolo según topología real.
- [ ] **Step 4:** PASS y validación de normalización con el mismo contrato que Java.
- [ ] **Step 5:** servidor Bedrock de staging propio; compatibilidad por versión; no trasladar PocketMine PHP a Java/Paper.
- [ ] **Step 6:** commit. Gate: lectura Bedrock probada con evidencias.

### Task 5: Estudio Minecraft legal y laboratorio de mecánicas
**Files:**
- Proposed: docs/minecraft/minecraft-mechanics-research.md; tests/fixtures/voxel_events.json
**Interfaces:**
- Consumes: versión exacta + Minecraft propio local + docs oficiales + motores abiertos de referencia.
- Produces: ficha para chunks/worldgen, entidades/pathfinding, inventario, combate, red/protocol, UI y comandos, con fuentes y restricciones de uso.
- [ ] **Step 1:** comprobar licencias/EULA del generador y el código que produce; registrar decisión de usarlo sólo localmente.
- [ ] **Step 2:** en PC propio ejecutar únicamente comandos documentados de inspección de versiones; no descompilar sin cumplir licencia.
- [ ] **Step 3:** contrastar conceptos con Luanti/VoxeLibre SIN trasplantar código sujeto a GPL ni fuentes propietarias.
- [ ] **Step 4:** crear pruebas deterministas de parsing de inventario/combat log con fixtures sintéticos.
- [ ] **Step 5:** publicar sólo fichas conceptuales y código original Kai, nunca archivos Java extraídos.
- [ ] **Step 6:** registrar evidencia y decisiones.

### Task 6: Combates Chuletón + Kai comentarista
**Files:**
- Existing: .agents/skills/kai-sololand-commentator/scripts/commentary.py
- Proposed: adapters/shared/combat-events.schema.json; tests/test_combat_events.py; .agents/skills/kai-sololand-commentator/scripts/event_bridge.py
**Interfaces:**
- Consumes: combat.started/hit/ended {match_id, sequence, edition, players, verified_source, timestamp}.
- Produces: frase narrada o [no_event], con deduplicación y rate limit.
- [ ] **Step 1 (rojo):** pruebas de ganador confirmado, evento duplicado, resultado ausente, participantes inválidos, eventos fuera de orden, publicación sin permiso.
- [ ] **Step 2:** python -m unittest tests.test_combat_events -v => falla puente inexistente.
- [ ] **Step 3:** flujo texto primero; la IA NUNCA inventa hit/ganador ni inyecta anuncios sin aprobación.
- [ ] **Step 4:** PASS más replay de combates simulados y logs redactados.
- [ ] **Step 5:** prueba en arena staging 1v1, no servidor público; voz opt-in después de texto.
- [ ] **Step 6:** commit, revisar artefactos y autorización. Gate: relato del ganador corresponde al resultado real.

### Task 7: Voz, personaje NPC y promoción progresiva
**Files:**
- Proposed: .agents/skills/kai-sololand-voice/SKILL.md; adapters/voice/voice_gateway.ts; tests/voice/voice_gateway.test.ts; docs/minecraft/deployment-gates.md
**Interfaces:**
- Consumes: texto validado + destino consentido + usuario/servidor que ha habilitado audio.
- Produces: audio o estado SILENT; sin retener voz de terceros sin base y aviso.
- [ ] **Step 1 (rojo):** tests de cancelación, consentimiento, límite de frecuencia, desconexión, inyección en chat y silencio por defecto.
- [ ] **Step 2:** node --test tests/voice/voice_gateway.test.ts => falta pasarela.
- [ ] **Step 3:** integrar TTS específico compatible con la versión de cliente/servidor; NPC visual Citizens/Paper o equivalente ÚNICAMENTE tras topología comprobada.
- [ ] **Step 4:** PASS de voz en localhost y pruebas de audición con operador voluntario.
- [ ] **Step 5:** piloto staging con revisión manual y rollback; por defecto observación/comentarios inocuos.
- [ ] **Step 6:** propuesta de PR y aprobación humana explícita antes de Sóloland.

## Arquitectura compartida / esquema mínimo
- Common intent: edition = java | bedrock | unknown; requested_action; target_scope; evidence_id; approval_status.
- Regla: unknown edition => discovery only. Posibles intents: observe, screenshot, narrate; chat y demás mutaciones requieren política y aprobación.
- Evento común: event_id, event_type, edition, server_id, match_id, sequence, source, verified, payload. Invalid source => quarantined, not published.
- Salida común: status = dry_run | observed | executed | blocked | unsupported; audit_id; redacted_error; no password fields.
- Repo architecture recommended: conservamos .agents/skills actuales; adaptadores nuevos en adapters/java, adapters/bedrock y adapters/shared. Rutas son propuestas hasta implementarse.
- Execution state NO garantiza éxito visible: CMD_ACCEPTED != EFFECT_OBSERVED != USER_SUCCESS_CRITERION.

## Estado de inicio y bloqueos observados
- Baseline remoto confirmado en GitHub: rama feat/codex-minecraft-pc-20261010, commit 5ceb7a7350cd86cbb46064a2588a1734e77beb14; 3 SKILL.md + scripts + runbook + tests/test_skills.py. Actualmente contiene 10 casos unittest visibles; no elevar una prueba local adicional a GitHub sin registrarla.
- Conector Remote Desktop Commander: PC Asier OFFLINE en la última comprobación (2026-10-10); también localhost OFFLINE. Impide validar inventario, launcher y runtime de Minecraft.
- Sóloland: software exacto de servidor, versión, permisos, sistemas de combate, hosting y políticas de plugin no comprobados. No modificar.
- Hugging Face: fuentes comunitarias útiles para investigación, pero acceso del conector específico de búsqueda falló en esta sesión; NO inventar resultados ni modelos disponibles.
- Estado de este artefacto: RESEARCH_BASELINE + EXECUTION_PLAN / CANDIDATE. No hay despliegue, integración con servidor ni copia de código externo.

## Decisiones de producto que cambiarían integración
1. ¿El servidor Sóloland es Java/Paper, Fabric/Forge, Bedrock Dedicated/PocketMine o mixto? Resolver con inventario y administrador.
2. ¿Actuará Kai como observador, bot jugador, NPC anclado, o actor móvil? Recomendar observador -> comentarista -> NPC.
3. ¿La voz se reproducirá por Discord, chat de proximidad en el juego o ambas? Seleccionar tras evaluación de consentimiento y latencia.
4. ¿Quién autoriza chat/bot/alteraciones en servidor y cuáles son los límites para un torneo en directo? Requiere aprobación concreta.
5. ¿Qué cuenta licenciada y entorno staging se usarán para Java/Bedrock sin suplantación o bypass de autenticación?

## Criterios de salida global
- 100 % de donantes con procedencia, licencia, SHA o commit y estado de incorporación.
- Todas las nuevas skills con SKILL.md, trigger claro, CLI real y tests correspondientes; rutas publicadas en GitHub.
- Pruebas Java y Bedrock separadas con una interfaz común verificada.
- Experimentos de voz y NPC fuera de producción; auditoría y modo de apagado.
- Drive PROJECT_MAP/wiki actualizados sólo cuando los cambios resulten verificados y pertinentes, conservando histórico.
