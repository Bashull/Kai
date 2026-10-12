# KAI Private PC Bridge — v0.1 STAGING

Estado: SOURCE STAGING; **no desplegado**, **no validación end-to-end**. No contiene secretos.

## Diseño
- Transferencia: cuenta Windows local independiente `kai_backup_sftp`, directorio NTFS `C:\KAI_PRIVATE_BRIDGE\sftp\incoming`; debe ser SFTP-only/chroot y restringida por ACL. El usuario no es administrador.
- Control de apps: servidor local Python estándar, solo `127.0.0.1`, autenticación Bearer, catálogo explícito de ejecutables habilitados por el usuario y auditoría JSONL. Nunca shell genérica ni UI remota por defecto.
- Próximo MCP: herramientas tipadas para list/status/launch y permisos explícitos por acción, con mediador autenticado y revocación. Ningún túnel público activado.
- Código probado fuera del PC (Python compile y 8 tests de seguridad); **no desplegado** en Windows ni expuesto en red.

## Bloqueo actual (2026-10-12)
La huella del servidor OpenSSH en el PC fue verificada desde el Galaxy, y la conexión TCP/22 funciona. Cuenta Windows `kai_backup_sftp`, carpeta y ACL creadas, sin secretos publicados. Los intentos de clave pública desde Android se rechazan. La modificación propuesta de `sshd_config` no pasó la validación en el entorno de ejecución; fue revertida desde su copia exacta **sin reiniciar SSHD**. El servicio previo sigue activo. El repositorio Restic externo y la restauración no se han realizado.

## Gate antes de habilitar
1. Resolver Windows OpenSSH key lookup / identidad de cuenta y validar configuración de forma independiente.
2. Probar SFTP canary y acceso fuera de directorios permitidos (debe denegarse).
3. Probar Restic cifrado con clave de recuperación custodiada fuera del móvil, `check --read-data`, restauración aislada y comparación de hashes.
4. Solo después habilitar backups automáticos y plan de actualización Termux.
5. Mantener la ruta anterior de recuperación hasta que el conector propio supere pruebas de paridad.

La rama es de staging y no debe fusionarse con main hasta que haya pruebas reales en PC y Galaxy.

## Actualización de ejecución real · 2026-10-12 20:17 Europe/Madrid
- **SFTP de KAI funcional**, sin modificar ni reiniciar el servicio original OpenSSH 22. Backend temporal original Win32-OpenSSH rechazó clave por mecanismo de Windows/LSA; cuenta Windows de ensayo `kai_backup_sftp` permanece deshabilitada.
- Reutilización **rclone v1.75.2** Windows (ZIP oficial GitHub SHA256 comparado con SHA256SUMS de la distribución: `8a9db2bad1dc79a65b3348fd857069598e2aab7cf4d118b77b1df23055aff818`), lanzado en `C:\KAI_PRIVATE_BRIDGE\bin\rclone.exe`. SSH SFTP por clave pública, carpeta única `C:\KAI_PRIVATE_BRIDGE\sftp\incoming`, escucha únicamente `192.168.1.12:2222` y regla Windows Firewall restringida a `192.168.1.11`; huella de host ED25519 validada fuera de banda y pineada en Termux. Ninguna clave privada se copió ni se publicó.
- Cliente SFTP Galaxy→PC: subió un canario de 21.930 bytes, lo descargó y comparó por SHA-256 exacto; Windows certificó también mismo SHA-256 `b3a283007ec6cf3f349eef8a114f3f21f7073f718eaa166574d559d82c415b5c`. Tarea Windows `KAI_Private_SFTP` bajo **LocalService**, disparador en arranque, `ExecutionTimeLimit=PT0S`, capaz de volver a atender el canario tras matar proceso provisional y arrancar tarea. **No hubo reinicio real de Windows**.
- Restic 0.19.1 Termux: repositorio cifrado externo `sftp:kai-pc-sftp:/restic-s24-recovery` inicializado, id prefijo `e4e85249f3`. Primer backup Restic de ruta Android guardó snapshot **parcial/error** por xattr `user.serial` de `/data/data` (preservar como diagnóstico), resuelto para el canario usando `restic backup --stdin-from-command -- tar ...`: `check --read-data` 4/4 packs sin errores y `restore latest` + extracción TAR y `cmp` PASS. Backup íntegro de `$PREFIX` en curso al documentar, NO etiquetar final hasta recibo.
- **Bloqueo de custodia**: la clave Restic vive dentro del HotVault local de Termux (puntero `~/.kai_secrets/restic_kai_s24_pc_20261012.pass`, modo 600) y un intento de transferencia automatizada del archivo de clave fue impedido por controles de seguridad. No intentar eludirlos. Una recuperación verdaderamente independiente del móvil requiere que el propietario deposite una copia de la clave en gestor de contraseñas o Cold Vault fuera del móvil. **No almacenar valores de secretos en GitHub/Drive**.
- **KAI PC Agent v0.1**, código de esta rama. Programa local `127.0.0.1:18761` con token solo privado en Windows y allowlist de aplicaciones. 8/8 pruebas Windows PASS. Invocado mediante Desktop Commander conectado a ChatGPT: `health` HTTP200; catálogo permite Bloc de notas; `launch notepad` HTTP202 y proceso nuevo `notepad.exe` verificado. Control remoto autenticado pero limitado a capacidades tipadas; **no es un plugin ChatGPT independiente ni control total de escritorio**.
- **MCP stdio adapter** `kai_pc_mcp_stdio.py` y `test_mcp_stdio.py` listos y probados directamente en el PC: 5/5 (initialize, tools/list, health, apps, rechazo de argumentos sobrantes). Puede instalarse en clientes locales MCP, pero no declara conexión autónoma a ChatGPT cloud.
- Mantener Remote Desktop Commander como camino de recuperación. Antes de promocionar a CANONICAL exigir recuperación externa de clave, backup completo HOME+PREFIX con hashes/restore independiente, arranque tras reboot, pruebas negativas de filesystem y permisos, control de GUI y permisos por acción. GitHub `main` intacta.



## Checkpoint operativo adicional · 2026-10-12 20:24 Madrid
KAI_Private_SFTP es una tarea Windows de arranque con principal LocalService, ejecución sin límite PT0S, batería permitida y hasta 3 reintentos; comprobado Running y SFTP autenticado desde Galaxy tras sustituir proceso provisional. No existe prueba de reboot físico aún. El PC Agent mantiene API únicamente 127.0.0.1:18761, y su launcher se colocó en Startup de la sesión Windows del usuario: tras finalizar el antiguo proceso se lanzó desde el propio archivo Startup, volvió a responder HTTP200 y el puerto escucha con nuevo PID. MCP stdio adapter kai_pc_mcp_stdio.py añadió herramientas kai_pc_health, kai_pc_list_apps, kai_pc_launch_allowlisted_app; test_mcp_stdio.py 5/5 pruebas correctas directamente en Windows. ChatGPT las acciona hoy mediante el puente ya instalado de Desktop Commander; no es instalación independiente de plugin cloud.
Restic synthetic TAR snapshot d7386d5e restaurada/check PASS. PREFIX se está respaldando por TAR (PID19079) y el próximo respaldo HOME NO ha comenzado; mantener gate CLOSED. No se ha movido la contraseña fuera del HotVault. Runbook autorizado en Drive: https://docs.google.com/document/d/1-iNjWuxVGqwVwjl99PkbsWIB42Ge72BBmbJihcIpvJU/edit .
