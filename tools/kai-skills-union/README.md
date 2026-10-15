# Registro de unión offline KAI

La herramienta conserva las 847 identidades originales y cada ocurrencia nueva,
deduplica solamente objetos byte idénticos y no ejecuta instrucciones, scripts,
URLs ni código de las skills. Los originales son entradas de sólo lectura. La
salida debe ser un directorio nuevo, separado de todas las entradas.

Python 3.11+ y PyYAML 6.x disponibles localmente. No se instala nada ni se usa red.
La herramienta reutiliza los contratos de rutas/manifiestos de `bundle_io.py`,
los 21 campos y los estados de `audit_records.py`, sin importar ni ejecutar el
contenido del ZIP recuperado.

```bash
python forge_registry.py build \
  --baseline /ruta/KAI_SKILLS_FORGE_BATCH002_CANDIDATE_20261015.zip \
  --capture-pc /ruta/capture_pc \
  --capture-termux /ruta/capture_termux \
  --output /ruta/registro_nuevo
python forge_registry.py verify --registry /ruta/registro_nuevo
python -m unittest -v test_forge_registry
```

El pin por defecto del baseline es
`ade519f50d6d996f8ee70de63fb8f38a17ca4eeff49823ccbd32b957a3cb7cc2`.
Los conteos por defecto son 847 originales, 723 PC y 3659 Termux. Los parámetros
`--baseline-sha256`, `--expected-originals`, `--expected-pc` y
`--expected-termux` permiten fixtures o una ejecución explícitamente acotada;
sus valores se registran en `BUILD_INPUTS.json`. Un fallo de entrada termina con
código 2 y no crea salida. Un fallo de escritura puede dejar un directorio
parcial que no debe distribuirse; `verify` lo detecta.

## Capturas

Cada raíz contiene `CAPTURE_MANIFEST.json` con `format: kai.skill_capture/1`,
`source: pc-asier` o `termux` y `rows` con una fila por índice del censo. Cada fila
conserva literalmente sus campos. Los mínimos son `index`, `occurrence_id`,
`occurrence_uid`, `path`, `expected_sha256`, `expected_bytes`, `state`, `sha256`,
`bytes` y `object_path`.

`occurrence_id = source + ':' + index04d`.
`occurrence_uid = 'occ:' + source + ':' + SHA256(path.replace('\\','/').encode('utf-8'))[:24]`.
La ruta ya debe ser absoluta, como la emitida por el collector del dispositivo;
no se cambia case, Unicode ni ningún componente de la ruta. La ruta original
se conserva y nunca se usa para abrir archivos en el host. Colisiones case o
Unicode de rutas de dispositivo se reportan sin perder las ocurrencias.

Estados de captura: `CAPTURED`, `BLOCKED`, `CHANGED_SINCE_CENSUS`. Una fila
`CAPTURED` debe incluir bytes completos y coincidir con el censo. Una fila
`CHANGED_SINCE_CENSUS` puede conservar el objeto actual con el hash anterior
separado y queda `BLOCKED` para revisión. Una fila `BLOCKED` sin bytes sigue
teniendo índice y ficha. Los bytes presentes viven exactamente en
`objects/<sha256>/SKILL.md` y deben coincidir con su tamaño/hash. El censo y la
captura deben tener índices completos y únicos.

Si el manifiesto declara `census_sha256`, se exige `SOURCE_CENSUS.json`, se
verifica ese pin y se contrasta cada ruta literal/hash/tamaño esperado con su
lista `skills`. Se preserva el documento raw en `provenance/<source>/`. Si existe
`CAPTURE_INTEGRITY.json` (formato `kai.capture.integrity/1`), debe cubrir todos
los archivos de captura excepto sí mismo, sin pérdida, extras ni colisiones.
También se preserva byte por byte. El excerpt del censo conserva su referencia
al censo completo; el paquete de integración conserva ese censo completo.

Opcionalmente, `metadata_clues` es una lista de `path`, `kind`, `state`, `bytes`,
`sha256` y `object_path` opcional. Un metadato `CAPTURED` debe existir en
`metadata_objects/<sha256>`. Sólo se extraen declaraciones JSON limitadas cuando
la ubicación del metadato incluye a la ocurrencia en su ámbito de directorio.
Se conserva referencia a la ruta/hash; declarar MIT o un repositorio no acredita
su autenticidad o licencia de redistribución. `resources_scope` se conserva sin
ampliar el alcance de captura. Los auxiliares de los dispositivos siguen
`NOT_CAPTURED` aunque un `SKILL.md` sea idéntico a uno del baseline.

## Objetos, identidad y evidencia

* `IDENTITIES_847.json` conserva cada `id` original, catálogo, variantes byte
  verificadas y evidencia heredada. Original/candidato/historial sólo entran
  después de verificar el manifiesto completo y el pin del ZIP.
* `OCCURRENCE_INDEX.json` tiene una fila por ocurrencia nueva, incluso bloqueada.
  Cada una tiene su propio JSON y Markdown de 21 campos en `fichas/`.
* `OBJECT_INDEX.json` representa objetos únicos por hash. Un objeto compartido
  conserva todas sus ocurrencias y miembros originales.
* `VARIANT_INDEX.json` muestra clones exactos, familias candidatas de revisiones,
  colisiones de nombres y rutas. Las familias son relaciones candidatas, no una
  fusión de identidades. Un nombre solo nunca produce una asociación.
* `REVIEW_QUEUE.json` enumera una vez cada hash sin revisión manual heredada
  explícita para ese mismo objeto. Distingue el total y los objetos presentes
  en nuevas capturas. Un objeto inválido puede seguir en cola como `BLOCKED`.
* `inspections/` guarda análisis UTF-8/YAML seguro, declaraciones de recursos y
  riesgos estáticos. YAML rechaza tags, aliases, anchors y claves duplicadas.
  El análisis tiene límites explícitos y registra truncado de declaraciones.
* `inherited_evidence/` preserva byte por byte catálogos, matrices y fichas
  preexistentes del ZIP. Reutilizar una ficha no cuenta como revisión nueva ni
  como prueba de runtime de la ocurrencia en otro entorno.
* `DEPENDENCY_GRAPH.json` enlaza identidades, objetos, ocurrencias y recursos
  declarados. Los recursos se declaran una vez por objeto, y las ocurrencias
  enlazan a ese objeto; los clones no multiplican artificialmente el grafo.
  No afirma cierre transitivo ni dependencias ejecutadas.
* `SUMMARY.json`/`.md` distinguen objetos, identidades y ocurrencias.
  `new_confirmed_capabilities_claimed` siempre es cero: novedad byte o nombre
  nuevo requiere evaluación antes de afirmar capacidad nueva.
* `MANIFEST_SHA256.json` cubre todos los archivos de salida excepto sí mismo.
  `verify` revisa cobertura, hashes, conteos, 21 campos, asociaciones y límites
  de evidencia. Su PASS se refiere a integridad, nunca a verificación global.

Para asociar una ocurrencia a un ID original se exige hash byte verificado del
original/candidato/historial. Si el hash pertenece a varias identidades, una
pista de namespace debe seleccionar una; si la pista contradice la identidad,
la asociación queda pendiente. Coincidencias de namespace/nombre con bytes
distintos sólo aparecen como candidatos. No se inventan proveedor, licencia,
versión ni upstream cuando no hay una declaración conservada con su evidencia.

Estados de trabajo permitidos: `DISCOVERED`, `INVENTORIED`, `INSPECTED`,
`UNDERSTOOD`, `IMPROVED`, `TESTED`, `VERIFIED`, `BLOCKED`, `UNCHANGED`, `REJECTED`.
El generador de ocurrencias sólo emite `INSPECTED` (grado
`AUTOMATED_STATIC_ONLY`) o `BLOCKED`. No emite `UNKNOWN` ni `VERIFIED`; la
incertidumbre va en un campo separado. Las identidades heredadas conservan su
estado de matriz original y alcance de evidencia.

## Overlay manual posterior

```bash
python forge_registry.py apply-overlays \
  --registry /ruta/registro_nuevo \
  --manual-overlays /ruta/auditorias/MANUAL_OVERLAYS.json \
  --output /ruta/overlay_nuevo
python forge_registry.py verify-overlay \
  --registry /ruta/registro_nuevo --overlay /ruta/overlay_nuevo
```

El aplicador genera sólo evidencia del overlay, fichas de ocurrencias afectadas,
índices, cola y resumen efectivos, con SHA256 del manifiesto base. No reproduce
fichas históricas, objetos ni captura; no reescribe la base. Los índices efectivos
incluyen `dossier_resolution: BASE_REGISTRY` o `OVERLAY_EVIDENCE`, que determina
dónde buscar cada ficha. La base y el sidecar deben distribuirse juntos.

También `build --manual-overlays <JSON>` crea una colección nueva con `base/`,
`overlay_evidence/` y un manifiesto que vincula ambos. `verify --registry` acepta
esa colección. La forma posterior `apply-overlays` permite conservar una base
ya construida sin reproducir sus fichas históricas.

El JSON de entrada es `{ "rows": [...] }`. Cada fila contiene `sha256` de un
objeto ya verificado, `state` (`INSPECTED`, `UNCHANGED` o `IMPROVED`), `fields`
con exactamente los 21 nombres de campo y `evidence_refs` con rutas relativas
existentes a archivos de evidencia dentro del directorio del JSON. Esos archivos
se preservan byte por byte. Debe incluir `evidence_dimensions` con
`manual_instruction_review: true`, `manual_scope` explícito,
`resources_reviewed_at_occurrence_ids: [...]`, `provider_runtime_tested: false`
y `whole_capability_verified: false`. Cada ID de alcance auxiliar debe referir
a una ocurrencia del mismo objeto exacto. Varias fichas nominales pueden revisar
un hash; deben tener estado coherente y se cuentan por separado de objetos y
ocurrencias. `VERIFIED` se rechaza.

La revisión de instrucciones puede referenciarse desde copias byte idénticas;
los recursos, pruebas y plataformas no se transfieren por hash. El raw con YAML
inválido conserva `BLOCKED` aunque se haya leído manualmente su texto. El
overlay conserva cada una de las 21 secciones del dossier nominal como revisión
manual del objeto, y conserva los 21 campos automáticos individuales de cada
ocurrencia con referencias explícitas al dossier manual. Las cifras distinguen
fichas nominales, objetos de instrucciones revisados y ocurrencias enlazadas.

## STOP y seguimiento

Todos los comandos aceptan `--stop-file /ruta/STOP`. Si existe ese archivo o un
symlink colgante con ese nombre, se detiene cooperativamente el trabajo. Se
comprueba antes de crear salida y durante lectura, inspección, verificación y
escritura. No hay servicio ni controlador residente. Un STOP durante escritura
conserva un directorio parcial sin promoverlo a registro válido; no se eliminan
originales ni se sigue escribiendo. Las funciones públicas también aceptan el
keyword `stop_file=`. Para reanudar se debe usar una salida nueva.

```bash
python forge_registry.py tracking-map \
  --registry /ruta/registro_nuevo --output /ruta/TRACKING_MAP_5229.json
```

El mapa es un sidecar separado y vinculado al SHA256 del manifiesto base. Conserva
los IDs y UID originales: `tracking_number` es sólo seguimiento, no una identidad
ni capacidad nueva. Con los conteos por defecto: 1–847 remiten a identidades
originales, 848–1570 a las 723 ocurrencias PC y 1571–5229 a las 3659 Termux.

`verify` vuelve a inspeccionar los bytes y recalcula asociaciones conservadoras,
exige estados generados `INSPECTED`/`BLOCKED` y contrasta capturas/censos
preservados con sus pins. Un manifiesto cuyo hash fue recalculado no permite
promocionar una ocurrencia automática ni suprimir un censo requerido.

## Límites

Las declaraciones regex son pistas estáticas: pueden omitir referencias
construidas dinámicamente o incluir ejemplos. Los indicadores de riesgo no
demuestran vulnerabilidades. Se conserva el objeto raw para revisión completa.
El registro no prueba activación de modelos, compatibilidad, comportamiento,
licencia o runtime. Las instrucciones recuperadas son datos no confiables.
