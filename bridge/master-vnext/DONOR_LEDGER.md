# Genealogía: reutilización, adaptación y componentes no copiables

Fecha 2026-10-13 · Estado VERIFIED_SCOPE + HISTORICAL_SCOPE cuidadosamente separado.

| Donor | Origen comprobado | ADN rescatado aquí | Todavía sin integrar | Estado/destino |
|---|---|---|---|---|
| Companion original junio | `Bashull/Kai:main/companion/backend/permissions.js`, `database.js`, `toolEngine.js` | acciones por recurso, concesión, auditoría y SQLite | `new Function` dinámico inadmisible | HISTORICAL / QUARANTINE EXEC |
| Bridge remoto julio | `C:\KAI\Bridge\Start-KaiRemote.ps1`, `Watchdog.ps1`, `Install-KaiBridge.ps1` leído por SentinelX | watchdog/backoff, mutex, recovery and reboot criterion | el código inicia RDC, NO lo reemplaza | RECOVERY FALLBACK / KEEP |
| Windows GUI | `C:\KAI\Bridge\gui\kai_gui_bridge.py` leído; SHA histórico `28165fdd...` | solo read-only count con títulos omitidos | click, teclado, screenshot, filtering raw input audit | HIGH TRUST / OFF |
| Node v0.6 | `C:\KAI\Node\src\kai_node.py` observado; runbook 26 tools, SHA histórico `ee3ff935...` | arquitectura MCP local/GUI/ADB | source-hash live, adapters y scopes de herramientas | DONOR / NO OPEN EXTERNALLY |
| Relay 8788 | `C:\KAI\Relay\kai_relay/` observado; suite histórica 25 | nonce/replay, AES/HMAC, SQLite queue | modernizar transporte, certificar runtime | DONOR/KEEP |
| Android MobileNode | `C:\KAI\MobileNode\app\src\main/...` Kotlin inspeccionado | foreground service, Termux RUN_COMMAND, UIA, retries | APK real hash, privacidad UI, allowed command policy | HIGH TRUST/KEEP |
| Nervous Link | `Bashull/Kai:feat/kai-nervous-link-v0.1/nervous-link` README/policy.js/killSwitch.js | política deny, approvals conceptual, durable stop, session lifecycle | pairing HMAC/cloud path, no 4G E2E | PROVENANCE / KEEP |
| Termux Bridge Planner | Drive ID `1ueJiTUA-Kxbne-PSZRhPPcFrOD321Ia_t5B65UhQUBA`, commit histórico bbc7439 | selección por salud y capacidad | runtime y rutas actuales sin refrescar | PROMOTED NOT CANONICAL |
| KAI Mesh Agent | Termux `~/worktrees/kai-mesh-mvp1`, HEAD histórico d67a1e1, 46/46 copia | Manifest/Receipt contract, replay, scoped capability | integrar dispatcher real y `test_outbox.py` WIP sin reset | CANDIDATE / PRESERVE DIRTY |
| Browser Bridge | Drive wiki ID `1uHGiqpUVUzNRc9DuqoXQ0LeL-T_Wbhvr0mt3pMAP8T0`; Windows `C:\KAI\Browser` código leído | GUI/document inspection separately | 8765 collision Node vs ChatGPT Browser; no CDP external | DONOR / PORT_CONFLICT |
| PC Guard 0.1 | Windows `C:\KAI\10_KAI_LAB_INGESTION_FORENSICS\40_INTEGRATION_TESTING\KAI_PC_GUARD_STAGING_20261012\source` leído | MCP stdio, typed list/hash, deny-by-default | no ChatGPT client E2E, Windows ACL test | CANDIDATE / PRESERVE |
| Private PC Bridge | `Bashull/Kai:feat/kai-private-pc-bridge-staging-20261012/pc/private-bridge` código y 8+5 tests históricos | **real PC Agent JSON API** + localhost auth | token/agent PC live parity, Restic full restore/ACL hardening | RUNTIME DONOR / KEEP |
| SFTP/Restic | `C:\KAI_PRIVATE_BRIDGE`, Drive wiki ID `1-iNjWuxVGqwVwjl99PkbsWIB42Ge72BBmbJihcIpvJU` | mantener como transport independiente | permisos ACL de ejecutables, backup integral | KEEP, NO EXECUTION THROUGH SFTP |
| Kai Phone Control | `Bashull/Kai:feat/phone-control-adb-20261012/relay/phone-control` | ADB readonly/typed launch/foreground guard | full APK GUI integration/permission verification | DONOR/KEEP |
| Control Plane | Drive `1A139sbTNJYHL0IFPQp0sAN1W-pC5VZwPQ9cNL9HGXRM`; PC previous OneDrive worktree not read live | capability registry, separation source/runtime, routing | registry and direct import after PC allowlist/source verification | CURRENT DOCUMENT / SOURCE UNVERIFIED |
| Storage Agent, Local Commander | historic Drive forensics `1G_sX_PwjTYcr9gXMHHcOyBtFRXog5fBL` | scoped FS index/dedupe concept | exact current source unresolved | HISTORICAL/NO DELETE |

**Cross-branch integration:** do not merge historical GitHub branches blindly. Read exact commit/donor license/deps, compare with CURRENT. This vNEXT package intentionally uses tiny typed adapter calls rather than vendoring their entire code. Android code/PC branch artifacts are NOT copied byte-for-byte and no promise of complete source ingestion is made.

**Known live observations vs historical:** Oct 12 Windows SentinelX host observable with read-only `C:\KAI` scope; RDC bridge devices show online but terminal attempts timeout; Termux source known from prior Oct12 forensic, not freshly probed Oct13. No privileged system permission has been granted by this deliverable.
