# Kai Termux Bridge v2

Puente persistente para operar un Termux autorizado sin depender de Remote Desktop Commander.

## Arquitectura

- Backend público: `https://kai-termux-bridge-v2.floot.app`
- Consola administrativa privada: MicroFn `Asier-Uceda-Royo/kai-termux-bridge-v2` (MCP enabled)
- Locator estable: `relay/locator-v2.json`
- Cliente: `relay/v2/kai_termux_bridge.py`
- Instalador: `relay/v2/install.sh`

## Seguridad

- La clave administrativa vive como secreto de MicroFn. No se guarda en el móvil ni en GitHub.
- Floot solo contiene el SHA-256 verificador de la clave administrativa.
- El pairing usa un código aleatorio de un solo uso con expiración de 10 minutos.
- Cada dispositivo recibe un token aleatorio propio; Floot almacena solo su SHA-256.
- La configuración del dispositivo se guarda en `~/.kai_termux_bridge_v2/config.json` con modo 0600; el directorio usa 0700.
- Toda comunicación usa HTTPS.

## Protocolo

1. `pair-init` crea un código temporal.
2. `pair-device` registra Termux y devuelve el token del dispositivo.
3. El cliente envía `heartbeat` y hace `pull` de la cola.
4. Los comandos se ejecutan mediante `sh -lc` con timeout máximo de 900 s.
5. stdout/stderr quedan limitados a 256 KiB por resultado y se entregan con `result`.
6. Los comandos entregados tienen lease: si no llega resultado, pueden ser reentregados. El cliente conserva caché/outbox para no repetir trabajo y reenviar resultados de forma idempotente.

## Instalación

Generar primero un pairing desde la consola administrativa. Después, en Termux:

```bash
curl -fsSL https://raw.githubusercontent.com/Bashull/Kai/main/relay/v2/install.sh | bash -s -- <PAIR_CODE>
```

El instalador descarga el cliente, empareja el dispositivo, inicia el daemon y crea un hook compatible con Termux:Boot.

## Operación local

```bash
kai-termux-bridge-v2 status
kai-termux-bridge-v2 once
kai-termux-bridge-v2 stop
tail -f ~/.kai_termux_bridge_v2/agent.log
```

## Fuentes de verdad

- Código cliente y locator: GitHub `Bashull/Kai`.
- Estado operativo/cola/resultados: Postgres administrado por Floot.
- Credencial administrativa: secreto privado de MicroFn.
- La versión v1 del relay se conserva separada como legado; v2 no la sobrescribe.
