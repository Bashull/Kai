# Mapa de sockets y relaciones, no telemetría de listeners

El siguiente inventario es **mapa histórico de configuración**, no una nueva lectura `netstat`/`ss`; la inspección del Windows `C:\KAI` vía SentinelX se restringe a ficheros y la lectura Termux por RDC no respondió. Nunca cerrar puertos en bloque.

| Puerto | Nodos y uso histórico | Política unificada |
|---|---|---|
| 22 TCP | OpenSSH original Windows | KEEP recovery; no interferir con SFTP2222 |
| 2222 TCP | SFTP rclone PC LAN, task LocalService | KEEP data plane; autorizar solo clave/dispositivo LAN, auditar ACL y hash |
| 18761 TCP | PC Agent Windows, 127.0.0.1 | KEEP typed control; token privado, no publicar |
| 8765 TCP | KAI Node MCP Windows; Browser ChatGPT loopback antiguo en PC; también puede existir Termux visor **en otro host** | COLLISION investigar PID/process/host antes de start/stop |
| 8788 TCP | Relay Windows local | KEEP hasta migración de mensajes y resultados |
| 8787 TCP | Nervous Link relay candidate | VERIFY (no abrir por defecto) |
| 8790 TCP | Kai Local Commander historical | SOURCE_UNLOCATED; no inferir listener |
| 7190,7192,19137,6464 | canales Android Bedrock/scrcpy Minecraft reportados históricamente | fuera del alcance de retirada del Master; NO TOCAR |

**Regla de ownership:** no inferir que `127.0.0.1:8765` significa el mismo servicio si cambias de Windows al Android. Identificar host → namespace/red → PID → ruta/binario → config → consumidores → efecto antes de cerrar. SFTP no se convierte en coladero de `watch folders` para ejecutar código. No publicar port forwarding global, NAT, Cloudflare quick tunnel o WebSockets anónimos. Hay un solo Gateway lógico, no un único puerto universal abierto por todas las aplicaciones.
