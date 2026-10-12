# KAI MASTER BRIDGE vNEXT — un único puente lógico

**Estado: LAB / IMPLEMENTED_CANDIDATE / NOT_DEPLOYED / NOT_CANONICAL.** 13-10-2026, UTC+2. No es todavía una alternativa remota operativa de ChatGPT a Windows/Android. Código libre en Python estándar y sin servidores ni puertos nuevos. No altera ningún servicio preexistente.

## Propósito y continuidad

Reutiliza los contratos y las interfaces ya construidas en KAI Node v0.6, PC Agent 0.1, Relay, Nervous Link, Termux MobileNode y Mesh. No contiene ni copia credenciales ni reemplaza los códigos donantes. El proceso Master es una **fachada local** que ofrece **MCP stdio**. Los agentes existentes permanecen adaptadores separados por nodo, proceso, identidad y autorización. SFTP/Restic sigue siendo **plano de datos y backup, no ejecutor**.

```text
ChatGPT (plugin a instalar y autorizar, aún NO conectado)
             |
   transport autenticado futuro, NO desplegado
             |
  KAI MASTER GATEWAY (MCP stdio local)
    identidad local / política por capacidad / kill switch
             |
  ActionManifest -> aprobación local -> SQLite idempotente -> ActionReceipt
             |
       +-----+------------------------+---------------------+
       |                              |                     |
  Windows PC Agent:18761      ADB Android autorizado    FS root read-only
  allowlisted apps            model/device/launch       list/SHA256
       |
  Node GUI (opt-in read-only metadata; HIGH TRUST)
       |
  Mesh/Relay/MobileNode: contrato a conectar con pruebas E2E
  SFTP 2222/SSH 22/Restic: quedan INDEPENDIENTES y sin modificaciones
```

## Capa de permisos (no confundir con privilegios del sistema)

El operador tiene derecho a configurar las capacidades del PC y Android **dentro de los permisos que realmente conceda cada SO**, con estas capas:

| Nivel | Operaciones | En esta versión |
|---|---|---|
| P0 Observe | estado local y catálogo de capacidades | `host.status` activo por defecto |
| P1 Read | listar raíz autorizada, SHA, salud y apps del PC Agent, estado/modelo ADB | implementadas, OFF por defecto |
| P2 Act | lanzar aplicación Windows de allowlist, iniciar app Android de allowlist | implementadas, OFF y exigen consentimiento local asociado a manifest |
| P3 High Trust | GUI metadata; futuro click, teclado, capturas, Android Accessibility, escritura/administrador | solo cuenta de ventanas, OFF y consentimiento; control completo NO integrado |
| P4 Emergency | cortacircuitos persistente STOP_ALL y recuperación offline | implementado localmente; no es herramienta MCP |

Tener ADB autorizado o Accessibility activado **no es root** ni concede leer datos privados de otras apps. Ni un token MCP ni un túnel anulan esas fronteras. Nunca se ejecuta una shell genérica; no hay `powershell.run`, `sh -lc`, borrado, modificación de archivos, instalación de APK, privilegios elevados ni puertos públicos. Se pueden añadir con permisos de propietario estrictamente acotados, en una entrega posterior con prueba física independiente.

## Componentes reales, sin duplicarlos

- **PC Agent**: la versión de Windows `127.0.0.1:18761` expone `/v1/health`, `/v1/apps`, `/v1/apps/launch` con token privado (Bashull/Kai rama `feat/kai-private-pc-bridge-staging-20261012`). Adaptador tipado usa `http.client` solo a loopback. La ruta de token se configura localmente y nunca se publica.
- **ADB**: el binario absoluto y el `serial` activo se pinchan en configuración del nodo. `devices`, `getprop ro.product.model` y `monkey -p ID 1` solo con paquete listado y aprobación externa. No usa `adb shell` abierto a órdenes arbitrarias. Una respuesta `submitted` **no** prueba el efecto visual.
- **FS de cada nodo**: lectura acotada de raíces físicas existentes, SHA-256 (máximo 64 MiB) y listado máximo 100; bloquea navegación `..`, rutas absolutas, rutas sensibles, symlinks y junctions. No implementa mutación (carreras de FS sin resolver).
- **GUI Windows**: para obtener un recuento de ventanas se reutiliza sin modificar el script real `C:\KAI\Bridge\gui\kai_gui_bridge.py` solo si está configurado; los títulos se descartan antes del recibo. No ofrece click/type.
- **Mesh/Relay/MobileNode**: conservar intactos hasta que se confirme el contrato real `ActionManifest -> ActionReceipt` en Termux y su source HEAD/dirty state. No hay un nuevo relay duplicado ni shell remota.
- **Nervous Link**: se hereda el diseño de parada persistente, antirrepetición y aprobaciones; esta implementación no pretende copiar su emparejamiento HMAC/red ni autenticar conexiones por Internet.

## Arranque aislado sin privilegios

Python 3.11+ con biblioteca estándar. Crear un directorio de laboratorio nuevo fuera de código desplegado y un `config.local.json` **privado**, basado en `config/config.example.json`. Mantener `host.status` como única capacidad activada inicialmente y un `state-dir` privado no compartido. Nunca pasar credenciales en parámetros de chat, ZIP ni repositorio.

```sh
cd kai_master_bridge_vnext
PYTHONPATH=. python -m unittest discover -s tests -v
PYTHONPATH=. python -m kai_master_bridge.cli --config config/config.local.json --state-dir ./private_state status
PYTHONPATH=. python -m kai_master_bridge.cli --config config/config.local.json --state-dir ./private_state mcp
```

Windows PowerShell: usar `$env:PYTHONPATH='.'; py -3 -m unittest discover -s tests -v` desde el directorio del proyecto. No reutilizar automáticamente las tareas Windows. En Termux el comando es idéntico cuando Python existe.

**Flujo de consentimiento de una acción sensible**: una acción enviada con UUID4, identidad de nodo, capability, parámetros exactos y deadline de hasta 5 minutos genera `PENDING_LOCAL_APPROVAL` + SHA-256 de manifiesto. El dueño comprueba el objetivo y **desde un terminal local del nodo** ejecuta `python -m kai_master_bridge.cli --config ... --state-dir ... approve UUID SHA256`. Solo una repetición idéntica antes del vencimiento puede ejecutarse, una vez. El consentimiento no puede darse por el propio MCP. Los recibos ejecutados o fallidos se reutilizan, evitando dobles efectos tras reintentos; un RUNNING interrumpido exige reconciliación manual.

**Parada**: ejecutar localmente `... stop` para crear `STOP_ALL`; `... unstop` solo desde el terminal del propietario. No se elimina ni se detiene ningún otro agente. El estado de parada no desactiva `host.status` pero bloquea otras operaciones.

## Seguridad y límites conocidos

- STDIO **no tiene autenticación remota**: requiere un cliente MCP local autorizado y nunca debe exponerse directamente a Internet. El acceso por móvil/web necesita canal autenticado aparte, usuario emparejado, doble comprobación de origen, autenticación fuerte y pruebas adversariales. El Gateway no declara esto resuelto.
- La aprobación local está protegida por la separación de superficie: el propio Gateway no ofrece aprobar, pero **un programa con acceso de escritura al SQLite local** podría falsificar concesiones. Por tanto, proteger directorio/ACL de estado es un gate de despliegue, no una formalidad.
- Limitación de carrera `symlink swap` durante lectura; no anunciar protección absoluta ante procesos locales hostiles. Windows reparse/junction con versiones anteriores a Python 3.12 exige comprobación específica.
- SQLite WAL/BEGIN IMMEDIATE + `synchronous=FULL` protege idempotencia básica y un fallo tras *claim* impide reejecutar automáticamente. No garantiza "exactly once" a través de agentes remotos hasta observar efectos y recibos del destino.
- Redacción: solo se registra request_id, nombre de capability, hash y estado, no cuerpos de entrada. El resultado solicitado sí puede ser devuelto al cliente y debe respetar las raíces autorizadas.
- No se verificó el PC Windows ni Termux en esta nueva ejecución. Las integraciones con PC Agent/ADB se probaron contra simuladores locales. La ruta física del token, la firma APK y los puertos de ambos nodos siguen siendo gates.

## Resultado de esta entrega

Suite reproducible bajo `python -W error::ResourceWarning -m unittest discover -s tests -q` con casos unitarios y emulador local de PC Agent, reintentos concurrentes, consentimiento, contención FS, rechazo de shell, límite de salida, parada y MCP stdio. Evidencia de ejecución en el informe Drive y `test_receipt.txt` del paquete.

**NO RETIRAR** Desktop Commander, Node, Relay, MobileNode, SFTP, SSH 22, PC Agent, Restic, Watchdogs ni borradores únicos. Consultar `RETIREMENT_RUNBOOK.md` antes de liberar espacio. Ninguna ruta del proyecto anterior es eliminada por esta entrega.
