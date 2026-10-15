# KAI Skills Auditor v0.4 / Archive v0.4.1

Offline inspection and reconciliation tools for an explicitly scoped collection of skill instruction documents. Donor scripts are read as data, never executed by the auditor. Provider services, credentials and functional validation are outside the archive's integrity claims.

Run `python -m unittest -v` in this directory. Python 3.10+ is required. PyYAML enables full frontmatter parsing for the auditor and bundle builder; the standalone bundle verifier uses the standard library.

`kai_skill_auditor.py --source INPUT --out NEW_OUTPUT --expected 847` reads existing `skills_*.json` capture batches. It rejects empty exact-root bodies, conflicting source revisions, missing indices, duplicate identities, invalid indices and existing output directories before producing a candidate archive.

`bundle_io.py ARCHIVE.zip` verifies complete manifest coverage, hashes, CRC, regular-file types and portable archive paths. This verification checks byte integrity and path structure; it does **not** check semantic consistency of the catalog. A self-consistent SHA-256 manifest also does not authenticate its publisher.

`--id ID --target NEW_LAB` previews an isolated copy and validates the complete governed catalog: unique positive integer IDs, provider/name/URI and root agreement, required SKILL.md hashes, original hashes if declared, resource counts and manifest totals. It rejects conflicting names, portable path collisions, existing targets and active skill roots before writing. `--apply` then copies only the explicit selection. This is a lab copier, not a production installer.

```sh
python bundle_io.py ARCHIVE.zip
python bundle_io.py ARCHIVE.zip --id 58 --target /path/to/new_lab
python bundle_io.py ARCHIVE.zip --id 58 --target /path/to/new_lab --apply --stop-file /path/to/STOP
```

The optional `--stop-file` uses an operator-selected existing STOP mechanism. Creating that marker requests cancellation; its contents are never read. Checks run before work, during verification, before staging and between files. STOP is cooperative and does not interrupt a write already in progress. No service or extra controller is created.

Verification and copying use the same open ZIP handle, and selected bytes are rechecked immediately before writing. On success, `STAGE_RECEIPT.json` records selected IDs, the manifest hash, and every staged source/path/size/SHA-256. The returned file count excludes the receipt. Staging files may be visible during copying; **visibility is not atomic**, and the receipt is written only after all selected payload writes succeed.

On failure or STOP, cleanup removes only files created by this operation and empty directories. Replaced paths or foreign content are preserved and reported as incomplete cleanup. Existing work is never recursively deleted or overwritten. Newly created parent directories above the target may remain.

`--rollback-target LAB` previews removal of a completed isolated staging copy; adding `--apply` removes that lab. It requires the staging receipt, an exact file/directory inventory and matching SHA-256/size for every payload. Modified, missing or extra material, symlinks, filesystem roots and active skill trees block the entire preflight before any deletion. It never follows symlinks or removes parent directories. Use it only for an isolated copy created by this tool:

```sh
python bundle_io.py --rollback-target /path/to/new_lab
python bundle_io.py --rollback-target /path/to/new_lab --apply --stop-file /path/to/STOP
```

Rollback rechecks files before unlink and retains the receipt until payload removal completes. It is not atomic: an I/O error, a concurrent change after preflight or STOP during removal can leave a partial lab and returns an error. Preserve the original ZIP for recovery; never treat an interrupted rollback as complete.

`build_bundle.py` is a task-specific reproducible builder consuming the six supplied archives and explicit local/cloud/provider recovery receipts. It is not a downloader or a universal upstream updater. Source archives, private catalogs and third-party resource collections are deliberately excluded from this Git repository.

`run_tool_checks.py --receipt NEW.json --stdout NEW.stdout.txt --stderr NEW.stderr.txt` runs only `test_*.py` from this toolkit directory. It installs nothing and does not activate optional donor tests. Outputs use exclusive creation and must not already exist. The receipt records passed/skipped/failed/error case counts separately and hashes every local `*.py` before and after the run. Failed subtest events are reported separately from failed case counts, so totals stay coherent.

The builders can consume this evidence with `--tool-test-receipt NEW.json`. A receipt is accepted only when its schema, exit code, case counts and complete current Python source hashes agree. Any source change invalidates it; generate the final receipt after code is stable. Without a receipt the historical builder records `0 / NOT_RUN`. The inherited `22/22 PASS` is explicitly historical, never a claim about a new build. A valid receipt is copied to build evidence. Optional fixtures skipped during default discovery remain counted as skipped, never as passed.

The prior staging checkpoint passed 22 inherited tests plus 20 security cases (42 total), including ambiguous catalog input, archive replacement, altered bytes after verification, prefix collisions, synthetic write failure, STOP and preservation of external data. Subsequent rollback and receipt checks have their own tests; use the current source-bound receipt for current totals. The recovered archive was checked against 7,105 payload hashes; ID 58 was copied to an isolated lab and its 46 payload hashes reread. This patch was tested on Linux; native Windows/Termux runtime compatibility still needs its own evidence. These are tool and packaging checks, not functional tests of 847 provider skills.


## Lotes incrementales consecutivos

La variante Batch002 reutiliza el toolkit del commit cb018c2e14618721de7bf48fa1a46839f0ae3814. Para continuar una distribución existente usa `build_incremental.py --batch-id 002 --base-bundle BASE.zip --base-sha256 SHA --candidates CANDIDATES --evidence EVIDENCE --output NEW_OUTPUT`. Cada ID de lote debe ser nuevo (`001`–`999`). Los ficheros sustituidos quedan bajo `HISTORICAL/before_batch_002/`; los originales y la evidencia de lotes previos conservan sus bytes. Un lote repetido se rechaza antes de escribir. El builder no certifica conducta de skills ni promueve evidencias copiadas.

La genealogía `candidate_change_batches` se reconstruye para todo el catálogo desde los `batch_NNN/CHANGES.json` ya verificados, incluidas filas heredadas que no se seleccionan de nuevo. Esto sólo recupera metadatos históricos; no atribuye modificaciones actuales a las filas no seleccionadas.

`audit_records.py` combina un catálogo previamente verificado, una matriz de dimensiones de evidencia y fichas manuales explícitas para generar21 campos por entrada. Las entradas sin revisión manual mantienen `NO_COMPROBADO` en comprensión, contratos, investigación y pruebas funcionales. Cobertura de fichas no equivale a auditoría profunda. El generador rechaza omisiones, identidades sin proveedor, overlays incompletos y promoción automática a `VERIFIED`.

## Federación OMEGA003

`capture_skills.py` recupera los cuerpos de un censo histórico fijo y conserva sus ocurrencias, rutas, índices, hashes y metadatos acotados. No ejecuta contenido capturado ni copia patrones de credenciales reconocidos. Usa únicamente un directorio de salida nuevo; `--stop-file` conserva las fuentes y puede dejar una captura parcial identificable. El censo de entrada debe tener un contador positivo. El escáner de patrones no demuestra ausencia de todos los secretos posibles.

`federated_registry.py` compone los847 originales de un bundle ya verificado con capturas PC/Termux fijadas por SHA. Verifica el manifiesto completo y los índices históricos antes de asignar alias ORI/PC/TMX; conserva los identificadores de ocurrencia anteriores. Reutiliza `bundle_io` para nombres, manifiestos y STOP. Rechaza bytes alterados, rutas peligrosas, cambios ocultos de censo, duplicación de colecciones y resultados preexistentes. Publica sólo en una carpeta nueva; una interrupción puede dejar salida parcial, nunca autoriza sobrescribirla.

El registro describe ocurrencias de documentos. Un grupo SHA demuestra bytes iguales; los grupos de texto normalizado sólo cambian finales de línea/espacios finales. Los nombres semejantes son candidatos para revisar. Ninguno demuestra equivalencia funcional, autoridad CURRENT, licencia transferible o compatibilidad. Los niveles L1 de esta captura no sustituyen fichas manuales anteriores: deben consultarse junto a su overlay y evidencia fechada. No se afirma inventario global de dispositivos fuera de las rutas del censo.

```sh
python federated_registry.py --original-root VERIFIED_EXTRACT --pc PC_CAPTURE.zip --pc-sha256 PIN_PC --termux TERMUX_CAPTURE.zip --termux-sha256 PIN_TMX --output NEW_REGISTRY --stop-file STOP
```

`quality_checks.py` ofrece contadores descriptivos para filas JSON suministradas, claves explícitas, frescura con reloj consciente de zona y proyección de cruces. Separa nulos, duplicados exactos, colisiones candidatas de normalización y fechas futuras. No repara datos ni inventa umbrales. Sus pruebas diferenciales usan SQLite con tipos de clave de texto y nulos; no prueban semántica de todos los motores de datos. El helper usa sólo stdlib; la federación requiere PyYAML disponible y revisado. No instala dependencias.

El recibo actual identifica el código y separa PASS/SKIP. Las pruebas del helper en Windows/Android sólo acreditan ese componente con datos sintéticos, no servicios de proveedor ni las5229 capacidades. Los corpus privados y cualquier material con licencia propietaria se conservan fuera del código público.

## Recursos comunes OMEGA004

`build_incremental.py` acepta opcionalmente `--provider-resources DIRECTORIO` y
`--resource-bindings ARCHIVO.json` juntos. El documento usa
`{"format":"kai.skills.provider-bindings/1","bindings":[{"id":2,"files":["providers/p/shared/contract.md"]}]}`.
Cada ID debe existir y cada recurso nuevo debe estar vinculado explícitamente.
Los archivos nuevos sólo pueden pertenecer al mismo proveedor y quedar fuera de
sus árboles de skills. Se pueden vincular auxiliares de skills hermanas ya
presentes en el bundle base verificado; no se pueden introducir ni sustituir por
esta vía, ni usar `SKILL.md` como auxiliar. Un cambio de recurso invalida los
consumidores cuyo hash no se haya actualizado explícitamente. Los recursos
sustituidos se conservan en el historial del lote.

`provider_resource_files` registra rutas, bytes y hashes independientes de los
contadores de archivos dentro de cada skill. `provider_resource_batches` no es
una revisión manual ni una evolución de las instrucciones de esas skills.
Una lista explícita no demuestra cierre transitivo: el runtime puede leer otros
archivos al ejecutarse. Comprobarlo requiere pruebas del consumidor real.

Cuando alguna selección tiene recursos comunes, `stage_selected` conserva
`providers/<namespace>/...` para todas las skills seleccionadas y deduplica los
recursos compartidos. El receipt `kai.skills.stage/2` declara raíces seleccionadas,
rutas auxiliares y todos los archivos copiados. Los auxiliares de una hermana no
incluyen su `SKILL.md` ni la seleccionan implícitamente. Sin recursos comunes se
conserva el formato plano anterior. El rollback admite ambos receipts, verifica
todo el inventario antes de borrar y mantiene los mismos límites de STOP e
interrupción. Sigue siendo una copia de laboratorio, sin registro ni instalación.

`task_drivers/omega004/test_dashboard_portability.mjs` ejecuta siete pruebas
de integración offline contra un proveedor suministrado por
`FORGE_PROVIDER_ROOT`. Comprueba runtime, preparación, evidencia suministrada,
límites de Node y rechazo de alteraciones. No incluye código propietario ni
instala dependencias. Sus resultados y hashes se registran por separado: el
recibo Python raíz no cubre los drivers anidados. Una preparación, compilación
o screenshot no certifica todos los conectores, accesibilidad o plataformas.

El manifiesto puede declarar `auxiliary_source_roots` para los orígenes de esos
auxiliares cuando una distribución contiene sólo parte del catálogo. Es un mapa
de procedencia de archivos: no añade IDs seleccionados ni permite copiar otra
entrada `SKILL.md`. Las rutas deben seguir perteneciendo al mismo proveedor.

`task_drivers/omega004/test_stage_support_stdlib.py` aporta cuatro pruebas
pequeñas para el mismo `bundle_io.py` en Linux, Windows y Termux: estructura,
rollback, preservación de cambios/archivos externos y STOP. No depende de PyYAML,
no ejecuta proveedores y conserva recibos separados por entorno. Estos cuatro
casos no forman parte del contador de descubrimiento Python en la raíz.

## Informe y continuidad OMEGA005

`task_drivers/omega005/evolve_reports005.py` recibe el ZIP privado004 y su SHA
esperado, exige los dos cuerpos de entrada exactos y genera un overlay nuevo.
Reutiliza los controles de rutas, escritura nueva, STOP, rollback y manifiestos
existentes. Añade dos referencias propias: una guía portable común y una guía de
afirmaciones, evidencia y revisión. Corrige la explicación de salida split en el
informe y mueve el enlace portable del dashboard a la referencia común. No cambia
el runtime protegido, las pruebas del proveedor ni sus licencias. El original y
la referencia local anterior quedan conservados por el builder incremental.

`test_evolution_boundaries.py` comprueba cuatro negativas con un ZIP suministrado
en `FORGE_BASE_BUNDLE` y `FORGE_BASE_SHA256`: pin incorrecto, STOP, destino existente
y ruta de instalación activa. `test_report_delivery.mjs` usa
`FORGE_PROVIDER_ROOT` y `FORGE_REPORT_PROJECT` para seis comprobaciones del contrato
de salida: bundle completo, HTML suelto, sidecar ausente o alterado, exportación
offline con el snapshot íntegro y corte de evidencia estable entre zonas horarias.
Los resultados de estos drivers se registran aparte del recibo Python de raíz.

El recibo raíz004 sólo se hereda si sus fuentes siguen coincidiendo; no se
presenta como una ejecución nueva005. Las pruebas upstream se conservan con sus
fallos literales y su alcance real. Ninguna compilación, comparación de texto o
prueba numérica acredita render, accesibilidad, conectores o instalación en un
host. El escenario de informe utiliza datos ficticios y dos ediciones de una
misma app, conserva su identidad y distingue fecha del corte de fecha de autoría.

`release_omega005.py` adapta el empaquetador existente y su verificador a nueve
candidatos. Requiere todos los inputs privados y evidencias locales; produce una
salida nueva y prueba staging/rollback sólo en su laboratorio. Las distribuciones
generales para destinos siguen retenidas hasta disponer de la evidencia adecuada.

## Conversión a documento OMEGA006

`task_drivers/omega006/evolve_document006.py` adapta únicamente la entrada privada
exacta0004 de un ZIP005 fijado y genera una salida nueva. Añade una referencia
propia de exportación y un helper de lectura. Reutiliza los527 recursos comunes y
auxiliares de0003; no incluye ni instala el runtime Documents del host.

`verify-local-export.mjs` reutiliza el verificador split existente y compara su
snapshot compilado con el fingerprint de `src/data.json`. Bloquea una edición
distinta o un bundle incompleto sin reconstruir la app. El CLI recibe
`--project-dir`; dentro de la skill resuelve el soporte relativo al proveedor.
La API importable admite un `providerRoot` verificado por el consumidor.
El resultado acredita coherencia de bytes en ese momento: no resuelve
presentación, exactitud de afirmaciones, render ni calidad del documento. Una
serialización JSON distinta se rechaza conservadoramente. No cubre otros layouts
ni promete protección atómica frente a cambios concurrentes.

`test_document_source.mjs` ejecuta siete casos con `FORGE_PROVIDER_ROOT` y
`FORGE_REPORT_PROJECT` ya verificados. Las cuatro negativas del generador usan
`FORGE_BASE_BUNDLE` y `FORGE_BASE_SHA256`. Sus recibos son independientes de la
suite raíz004 heredada; los drivers anidados siguen fuera de ese contador.

La conversión real sigue la skill Documents canónica disponible, con su runtime,
autoría, renderer y lectura de páginas. El preset o destino debe existir de
verdad. La inspección OOXML/accesibilidad estructural y el render del DOCX no son
certificación de tecnología asistiva ni pruebas de la app en navegador. La
entrega local no acredita entrega nativa Google Docs. El driver de release006
reutiliza el verificador existente para diez candidatos y laboratorio aislado.
