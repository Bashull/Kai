# KAI HyperBridge

Behavior Pack for Minecraft Bedrock that emits structured, direct in-engine telemetry for Kai.

## Transport
The Android client cannot use `@minecraft/server-net`; telemetry is emitted with `console.warn()` using:
- `KAIHB|BOOT|{json}`
- `KAIHB|CAP|{json}`
- `KAIHB|STATE|{json}`
- `KAIHB|EVENT|{json}`
- `KAIHB|ERROR|{json}`

Termux consumes the Content Log / logcat stream and writes a low-latency machine-readable state.

## Safety
Read-only world bridge. It does not teleport, kill, spawn, alter blocks, or issue commands.
