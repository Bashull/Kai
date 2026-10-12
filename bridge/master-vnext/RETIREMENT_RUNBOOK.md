# Retiro de bocetos y puertos antiguos — prohibición de limpieza ciega

**Estado 2026-10-13:** 0 archivos de terceros borrados · 0 servicios/parches/tareas detenidos · 0 puertos alterados · 0 backups eliminados.

La orden del propietario de retirar los antecesores al finalizar la integración queda **aprobada en intención**, pero **condicionada a pruebas**. Que haya una cápsula de código no garantiza que sobreviva el entorno de ejecución. Un proyecto en WIP o un hash único jamás se declara duplicado solo por nombre.

## Pruebas bloqueantes para permitir retirada, con recibos firmes

1. `[ ]` **Inventario físico** de nodos Android/Termux/Windows/OneDrive, PID, tarea, ruta, alias, puertos/listeners, configuraciones y procesos consumidores; snapshots actuales exactos, no estados históricos. Conservar `test_outbox.py` WIP intacto.
2. `[ ]` **Código único preservado**, hashes actuales de todos los donantes, versiones licencias/dependencias y mapeo de toda capacidad/memoria/entrada-salida al nuevo código. Revisión de equivalencia; no solo ZIP.
3. `[ ]` **Recuperación independiente** RESTIC HOME+PREFIX+datos/runtimes con verificación de lectura completa, prueba de restore aislada, custodia de clave fuera móvil; restore Windows Node/Relay/GUI/PC Agent y manifiesto de secretos solo punteros.
4. `[ ]` **Permisos seguros**, revisión de ACL Windows para servicio LocalService y ejecutables SFTP, sin tocar la reserva de Kai Agent sin orden expresa; Android Accessibility/ADB/Termux permisos autorizados normalmente por usuario y firma de APK.
5. `[ ]` **Gateway E2E** desde cliente ChatGPT independiente de RDC: identidad mutuamente autenticada, ejemplo host.status, prueba de lectura/hash, recibo idempotente y protección antireplay.
6. `[ ]` **Actuación controlada**: app launch Windows + Android aprobadas, GUI metadata → input puntual con pantalla/paquete comprobado antes/después; rechazo de acciones fuera del consentimiento.
7. `[ ]` **Fallos y recovery**: desconectar RDC y validar desde la ruta propia SIN eliminarlo, reiniciar Windows y Android/Termux, cambio LAN↔5G, reconexión, kill switch/ revocación, rollback documentados y aprobados.
8. `[ ]` **Paridad y observación** durante periodo con los servicios antiguos como fallback, sin conflict o drift; emitir per-component retirement certificate con hashes, rollback, dependientes y evidencia.

## Candidatos, no órdenes de eliminación

| Donante | Ocupación/puerto histórico | Decisión actual | Qué retiraría únicamente al pasar gate |
|---|---|---|---|
| `C:\KAI\Bridge` y tareas `Kai PC Bridge *` | RDC watchdog, sin puerto propio | KEEP | tareas RDC solamente al demostrar fallback alternativo |
| `C:\KAI\Node` | 127.0.0.1:8765 | KEEP | duplicación runtime sin consumidor tras reemplazo verificado; conservar código único |
| `C:\KAI\Browser\kai_chatgpt_local_bridge_server.py` | 127.0.0.1:8765 | INVESTIGATE_COLLISION | deshabilitar solo listener cuya función esté absorbida, con PID probado |
| `C:\KAI\Relay` | 127.0.0.1:8788 | KEEP | migrar cola y estado sin perder resultados; apagar tras vaciado firmado |
| Nervous Link | 8787 local, transporte externo | SOURCE_KEEP | scripts de arranque obsoletos tras sesión/replay parity |
| Windows PC Agent | 127.0.0.1:18761 | REQUIRED | no retirar: adaptador maestro depende de él |
| SFTP Rclone | LAN 2222 | REQUIRED | no retirar: data plane/backups |
| Windows OpenSSH | 22 | RECOVERY | no retirar por sustituir RDC |
| Android Termux runit | distintos puertos/servicios | KEEP | solo servicios sobrantes verificados como no consumidores |
| MobileNode/Accessibility | app Android | KEEP | app nueva firmada e instalable + migración de permisos/datos/identidad; no desinstalar sin copia |
| Capabilities y worktrees Git locales | sin puerto | NO DELETE UNIQUE | snapshots redundantes solo tras comparación byte/hash y Recovery Capsule |

### Método de ejecución, cuando todos los gates estén verificados

1. Generar `retirement_candidate_<component>.json` individual: estado, owner, hash, runtime PID/tarea, puerto y binds reales, dependencias, usuarios, backup/restore hash, certificado de equivalencia, script deshabilitar sin borrar y rollback probado.
2. Paso temporal y reversible: **deshabilitar** una tarea/servicio NO necesitado, no matar proceso a lo bruto ni eliminar archivos; test de salud, seguridad, CPU/disco y reconexión.
3. Periodo de observación; si falla, rehabilitar desde registro exacto, registrar incidente.
4. Solo con OK de pruebas, borrar **esa ruta específica** certificada mediante operación con confirmación, no carpetas genéricas, volúmenes, secretos ni `.git` WIP. Registrar bytes reales liberados y puertos efectivamente cerrados. Sin acceso físico y sin evidencia no se ejecuta.

### Dos correcciones importantes

- El `C:\KAI\Bridge\SelfTest-Recovery.ps1` existente **mata deliberadamente Desktop Commander** como parte de la prueba. Nunca usarlo durante esta migración sin una ventana de recuperación protegida.
- El README de Node 0.2/16 está desfasado frente al código v0.6/26 observado en octubre. No borrar nada por leer una documentación superseded.
