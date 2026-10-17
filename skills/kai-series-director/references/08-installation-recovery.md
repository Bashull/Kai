# Runbook: instalación, convivencia y recuperación

## Alcance de este paquete
`0.4.1-MULTIHOST-CANDIDATE`: portación compatible basada en investigación documental + nueva CLI estática; **NO** reemplaza ni fusiona el original de Work v0.3.1 (commit documentado ec3256ee…), cuyas 15 referencias, scripts y 99 tests no están incluidos en este ZIP. El nombre de habilidad es el mismo para poder invocarla en un entorno local donde el original no existe. Si se encuentra una versión instalada, abortar reemplazo y comparar antes.

## Dependencias
Python 3.10+ estándar (para CLI/tests); Markdown para leer el Skill. Sin modelos descargados, claves, red, API de proveedores ni servicios en background. Uso local de `python scripts/director_gate.py fixtures/film_plan.json`.

## Instalación segura PC Codex
1. Confirmar ruta del usuario `%USERPROFILE%\.codex\skills` y buscar `kai-series-director` ya existente. Si existe, NO sobreescribir: crear copia de evaluación en staging y hacer diff.
2. Copiar los archivos completos de este paquete en `...\skills\kai-series-director` cuando esa carpeta esté libre. Registrar hashes y fecha, sin modificar memoria global.
3. Ejecutar `python -m unittest discover -s tests -v` y `python scripts/director_gate.py fixtures/film_plan.json` en el directorio instalado.
4. Confirmar que el host/cliente de Codex reconoce la skill. No presumir recarga en caliente; reiniciar sesión si el cliente lo requiere. La instalación en Codex del PC NO instala habilidades automáticamente en el runtime de ChatGPT de esta conversación.
5. Registrar receipt local y en Drive/registro del proyecto, con modalidad REAL/NOT_VERIFIED.

## Reversión
Como el directorio de destino previo se exige ausente, desinstalar esta copia implica borrar únicamente su carpeta creada y restaurar la fuente anterior si se identificó una. Cualquier archivo externo modificado requiere backup/diff por separado; este paquete no contiene automatismo de borrado.

## Alineación Work v0.3.1
Recuperar el árbol original, revisar SKILL.md/15 guías/scripts/schema, comparar nuevas reglas, insertar manuales selectivos sin duplicación, ejecutar 99 tests previos + 15 nuevas (si el merge lo permite), generar smoke de una escena real y reportar `media NOT_RUN` si no se ejecuta. Commit en rama de integración, PR y writeback de pruebas. No proclamar versión unificada hasta ese resultado.
