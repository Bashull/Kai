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