# KAI Harvester Fusion v0.2.1 · Termux-first, local-only
Estado **CANDIDATE, no producción**. v0.1 se conserva e instala junto a v0.2, sin sobrescribirla.

## Instalación en Termux
Desde este directorio: `bash termux-install-v02.sh`.
Nuevo comando: `kai-harvest-v021 doctor`, `kai-harvest-v021 scan-zip <ZIP>`, `kai-harvest-v021 --root <corpus> ingest <ZIP>`, `kai-harvest-v021 --root <corpus> index`, `kai-harvest-v021 --root <corpus> search 'frase'`, `kai-harvest-v021 --root <corpus> assets`, `kai-harvest-v021 --root <corpus> compare-manifest <otro-manifest.json>`, `kai-harvest-v021 rate-policy 429 --retry-after 90`.
Los comandos anteriores `kai-harvest` siguen siendo v0.1 y funcionan sin esta versión.

## MCP / habilidad ChatGPT
`python -m kai_harvester.mcp_bridge --root <corpus>`: servidor **STDIO experimental de solo lectura** para clientes MCP compatibles. No conecta ChatGPT automáticamente, requiere configurar acceso explícito. Skill `skill/SKILL.md` es receta portable, no complemento ya instalado en ChatGPT.

## Seguridad
El índice FTS local cubre todas las ramas PRESENTES en el RAW, no versiones ausentes ni assets no recuperados. Los retornos jamás son certificado de export completo. No se guarda autorización de ChatGPT ni se activa tarea de autoarranque, backup, servicio o conectividad externa. Restic/rclone/Termux:API solo como diseños opt-in hasta pruebas y autorización.

## Alcance
Conserva código v0.1, 18 tests originales, añade tests de FTS5/búsqueda y rate/MCP. 18 nuevos repos detectados con READMEs acotados; no se afirma ingesta semántica completa de todos sus archivos. NO se altera GitHub ni se borra material histórico.

**ZIP gigantes:** `scan-zip` analiza metadatos sin descomprimir; puede inspeccionar un ZIP de 10+GB, pero **no** ingiere todos sus bytes. El importador real sigue limitado por diseño a 512 MiB de archivo y 2 GiB descomprimidos; superar eso exige streaming con cuotas/ensayos y se considera pendiente, no resuelto.


## Skills locales del móvil
`skills/` contiene tres recetas nuevas para agentes CLI. Tras pruebas se pueden copiar a `~/.agents/skills/` sin sobrescribir otras. **No son plugins instalados en ChatGPT alojado**.

**Patch v0.2.1:** Android platform doctor fixed, ZIP symlink/encrypted flags, MCP parser request-id stale state fixed. V0.2 remains rollback, 0.2.1 installed alongside.
