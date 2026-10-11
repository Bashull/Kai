# Donor Extension Atlas · v0.2 (VERIFY_SCOPE, NOT_FULL_INVENTORY)
Los 18 repositorios fueron localizados en GitHub y se leyeron READMEs representativos de 11; NO se clonó ni estudió todo su código. Diseño adaptado, código nuevo propio.

| Repo | Célula y transfer | Estado y precaución |
| --- | --- | --- |
| termux/termux-app | Runtime Android; diagnóstico de entorno | Sistema presente, NO modificar APK |
| termux/termux-api | Dispositivos/avisos Android | App y permisos no confirmados; GPLv3: no copiar código |
| termux/termux-api-package | Comandos CLI de Android | termux-api 0.60.0 presente |
| termux/termux-boot | Arranque programado | NO activar sin consentimiento; firmas coherentes |
| termux/termux-tasker | Jobs con intención explícita | No instalada ni habilitada por v0.2 |
| termux/termux-packages | Recetas reproducibles AArch64 | Ya hay Python 3.14; no reinstalar |
| termux/termux-services | Supervisor runit | Presente pero NO habilitamos daemon |
| termux/proot-distro | Aislamiento Linux sin root | Presente; no imprescindible al CLI ligero |
| restic/restic | Backups cifrados verificados | Instalada; nunca copiar secretos ni activar sin Vault |
| rclone/rclone | Réplicas controladas cloud | Instalada; no inspeccionar ~/.config/rclone |
| syncthing/syncthing | P2P de replicas | Investigado, NO instalado |
| simonw/sqlite-utils | Índices, consultas, FTS | FTS5 en SQLite stdlib, sin dependencia nueva |
| asg017/sqlite-vec | Retrieval vectorial futuro | Pre-v1, ABI Android sin prueba; NO instalar |
| simonw/datasette | Vista local de SQLite | No instalado; UI solo loopback cuando se autorice |
| microsoft/markitdown | Conversión estructural de assets | Alto coste de deps; NO requerido para RAW |
| modelcontextprotocol/python-sdk | Interoperabilidad MCP stdio | Patrón de contrato; adaptador stdio experimental propio |
| microsoft/playwright | Fixture navegador E2E | Requiere entorno de navegador distinto, NO en Termux |
| openai/skills | Empaquetado de skills | Skill Markdown portable, NO autoinstalado en ChatGPT |

REUSE -> ADAPT -> COMPOSE. Las licencias deben revalidarse por commit antes de vendorizar código; ninguna fuente de terceros fue copiada. Cada capacidad candidata queda NOT_PROMOTED hasta prueba real adecuada.
