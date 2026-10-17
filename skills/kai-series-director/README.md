# KAI Series Director · 0.4.1-MULTIHOST-CANDIDATE

Extensión compatible y **reversible** para Codex en Termux/Codex local y candidata para PC. No es el árbol Work v0.3.1: depende documentalmente de él, sin reemplazarlo, y declara `SOURCE_RECOVERY_PENDING`.

**Incluye:** SKILL.md; 8 manuales especializados; gate de planificación JSON 100% local; dos fixtures; 17 pruebas unitarias; manifiesto de hashes. Los repositorios externos se citan como donantes, no están incorporados ni instalados.

**Primero:** `python -m unittest discover -s tests -v`.

**Después:** `python scripts/director_gate.py fixtures/film_plan.json`.

**Criterio:** esta herramienta es un **preflight estático**. No ejecuta vídeo, audio, proveedores o juegos, no concede autorización de gasto/generación, no juzga derechos jurídicos y NO sustituye revisión humana.

Documentación de instalación/reversión: `references/08-installation-recovery.md`.

PC offline: `powershell -File tools/install_pc.ps1 -ZipPath <downloaded_zip> -ExpectedSha256 <exact_hash>`; el script de instalación no modifica el origen Work y aborta si hay skill previa.
