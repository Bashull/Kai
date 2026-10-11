# Donor registry and Capability DNA

Retrieved 2026-10-11 via GitHub connector and web; the investigation sampled READMEs, architectural docs and focused code paths. Repository **full code + full historical issues/commits were NOT ingested** (container network unavailable). SHA values below refer to specific inspected files, not repository commits. Additional claims inherited from chat alerts remain historical until independently reverified.

| Donor | Inspected cells / evidence | Transfer / decision |
|---|---|---|
| [siraht/ChatGPTExporter](https://github.com/siraht/ChatGPTExporter) | `src/chatgpt/inventory.ts` blob `ae0cfccd...`, `src/chatgpt/endpoints.ts`, `docs/ARCHITECTURE.md` blob `01f89af2...`, `docs/WEB_CONTRACT.md` blob `51f77dac...` | Independent scope ledgers, raw pages and terminal cursor proofs; strict typed bridge. ADAPT concepts, no source copying. |
| [harris-ahmad/chatliberate](https://github.com/harris-ahmad/chatliberate) | `packages/core/src/branches.ts` blob `765bdc44...`; README blob `09189965...` | Children UNION parent-backlinks, branches, active path; regenerated answers. REIMPLEMENT in iterative Python. |
| [OwlCt/ChatGPT-Export](https://github.com/OwlCt/ChatGPT-Export) | README blob `83fa33b7...`; `Tampermonkey.js` blob `8a3eb2d0...` | Paired raw/readable export, offline reader, project asset context. ADAPT as static index; no remote vendor libraries. |
| [D1DX/chatgpt-helper](https://github.com/D1DX/chatgpt-helper) | `popup.js` blob `b8dd3fb1...`, README | Source×Fetch×Output validation, by-IDs retry, checkpoint UX, manual attachment-only restoration. CANDIDATE for vNEXT. |
| [sisodiabhumca/AI-Exporter](https://github.com/sisodiabhumca/AI-Exporter) | `extension/lib/api.js` blob `3981596a...`, `extension/manifest.json` blob `715f9fa9...`, README | Workspace/account resolution, rate backoff, portable RAG, compliance manifest. ADAPT workspaces; avoid broad host permissions in KAI. |
| [pionxzh/chatgpt-exporter](https://github.com/pionxzh/chatgpt-exporter) | `src/api.ts` blob `1902632c...`, `src/exporter/json.ts` blob `419b1451...`, README | Split raw vs materialized image assets, JSON ZIP dedup, render fidelity, Temporary Chat observation. CANDIDATE for later asset bridge; basic raw integrity already adapted. |

## Historical issues/commits supplied by the chat (not re-fetched as part of implementation)

- Project cursor invalid: https://github.com/siraht/ChatGPTExporter/issues/4
- Broken singular/conversations batch detail: https://github.com/siraht/ChatGPTExporter/issues/5
- Business authentication: https://github.com/sisodiabhumca/AI-Exporter/issues/7
- Project asset contextual 403: https://github.com/OwlCt/ChatGPT-Export/issues/1
- 429 false empty inventory: https://github.com/pionxzh/chatgpt-exporter/commit/1715ca717e1779ef7352a3855f26736bfca30005
- RAW map fidelity: https://github.com/pionxzh/chatgpt-exporter/commit/fc910b5ef3a5750eba331f37f693aa773a1068fd
- ZIP asset mode: https://github.com/pionxzh/chatgpt-exporter/commit/82ec4bcfea9f6c651393861dbdf7c8eae8330045
- Rendering source text fidelity: https://github.com/pionxzh/chatgpt-exporter/commit/4c8fe6ea01d58a59bc59aea9ba1421fee7d80969

## Licensing

Sources identified as MIT from inspected LICENSE/README for several donors. This new implementation uses no copied code; license texts of all six need line-by-line legal/commit verification before source-level vendoring. Dependency-free Python and native browser APIs reduce license propagation.

## Transfer ×3

- DIRECT: offline forensic ingestion, branch inspection, evidence audit, conservative scope capture.
- TRANSVERSAL: chat/data export evidence integrity for other SaaS systems.
- EMERGENTE: composite completeness certificate + restartable work journal; future app connector support, but no current authorization or implementation.

## Genealogy and no-retirement policy

Upstream six repos remain DONORS. KAI Devourer CURRENT remains CURRENT; this pack is a self-contained CANDIDATE and never auto-retires a donor or moves an old artifact. No unique material is authorized for deletion.

## Second-pass source review · 2026-10-11

Six additional cells opened: `siraht/src/core/request-control.ts` blob `1a4a1a91...` (pause/resume/cancel, bounded concurrency, Retry-After + jitter); `chatliberate/packages/core/test/resume.test.js` blob `ab27de5c...` (skip IDs and target selection); `OwlCt/test/reader.test.js` blob `c16906c3...` (browser IndexedDB, local vendored reader assets and UI regressions); `D1DX/content.js` blob `e62f9cd4...` (unified source selection, checkpoint storage, 100 MiB volume heuristic, adaptive backoff); `AI-Exporter/extension/lib/exporter.js` blob `ed12533c...` (separate project knowledge files, error manifest); `pionxzh/tests/rate-limit-error.test.ts` blob `b107be36...` (Retry-After origin vs fallback distinction). Findings feed vNEXT test matrix; nothing was copied verbatim.

A useful discrepancy: some upstream implementations favor infinite/very long retries or log raw error bodies, while KAI v0.1 deliberately fails closed after bounded retries and avoids logging potentially private response bodies. This protects safe status but sacrifices unattended marathon exports, to be addressed by a tested persisted rate governor rather than unbounded loops.
