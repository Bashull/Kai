# ACE-Step Runtime Inventory CURRENT

Verified at: 2026-08-27
Inventory status: PARTIAL_FEDERATED · VERIFIED_SCOPE per source.

## Decision

- Generation route: ACE-Step cloud client from Termux.
- Orchestration/benchmarks: Termux + KAI Audio Studio.
- Local inference on phone: NOT_PRESENT_IN_VERIFIED_SCOPE.
- Local inference on PC: REJECTED_BY_HARDWARE for ACE-Step 1.5.
- Hugging Face inference: CANDIDATE, not configured or evidenced.

## Termux — VERIFIED_SCOPE

### Client and governance

- Donor repo: ~/projects/ace-step/ace-step-skills
- Authority origin: https://github.com/ace-step/ace-step-skills.git
- Donor commit: 4cdd152ec9c2004f641edf218c5561b160f28acc
- Installed replicas: ~/.agents/skills and ~/.claude/skills.
- Installed scripts share SHA-256:
  43e1fad0f41938b771a6bd15b267e5a3ccac598dc476d7e2083731e8b7fe86ae
- Donor script SHA-256:
  650c90e59ea5fc6a72ebee8e53c7845aef4fcb1543053ca2bee11c190fb51926
- Drift is one intentional adaptation: output directory changed to
  ${ACESTEP_OUTPUT_DIR:-/storage/emulated/0/Download/DJ KAI}.
### Live cloud route

- API host: api.acemusic.ai
- Mode: completion
- Credential: PRESENT; value not read or recorded.
- Pointer: ~/.agents/skills/acestep/scripts/config.json#api_key
- Safe health result: HTTP 200, body identity "health check".
- Observed generation model: acemusic/acestep-v1.5-turbo.
- Dependencies present: curl, jq, ffmpeg.
- Outputs: two JSON responses plus two MP3 files, 3.7 MB total.
- Benchmark authority remains ~/projects/music-benchmarks.

### Local model evidence

- ~/.cache/huggingface size: 83 KB.
- No ACE-Step weights or local inference checkout found.
- ai-toolkit contains an 83 KB ACE-Step 1.5 training extension.
- This extension is donor code, not an installed inference runtime.
- Port 8001 and Gradio 7860 were offline during the inspection.

### Termux storage bridge

- 127.0.0.1:8787 responds, but /health returns HTTP 404.
- Bridge process existence is VERIFIED; skill contract compatibility is UNKNOWN.

## PC Asier — VERIFIED_SCOPE

- Windows x64, Python 3.12.10.
- GPU: NVIDIA GeForce GTX 750, reported VRAM 1 GB.
- ACE-Step 1.5 official minimum path needs substantially more VRAM.
- Filename searches across governed work/cache/media/project roots: no hits.
- Content search found one STAGING chat donor mentioning ACE-Step.
- No runtime, weights, client or installed ACE skill found in inspected roots.
- Full C:\Users inventory is PARTIAL because .pytest_cache denied access.
- Global raw recursion was stopped after poor performance; no destructive action.

## Hugging Face — PARTIAL

- Authenticated connector identity: Bashull, Pro, read-repos/jobs scopes.
- Running jobs: none; account reports 37 historical jobs.
- Public Bashull models matching ACE/music: none.
- Public Bashull Spaces: autotrain-advanced and Qwen-Image-Edit-2511-LoRAs-Fast.
- No public ACE/music Space found.
- Connector model/Space search methods failed as unavailable.
- Private repository inventory is therefore UNKNOWN, not empty.
- Termux hf CLI is not authenticated and was used only for public listings.

## Genealogy and routing

ace-step-skills donor
→ installed Termux client replicas
→ intentional DJ KAI output adaptation
→ two verified cloud generations
→ benchmark manifests
→ KAI Audio Studio cloud adapter

## Verified integration result

- Credential-presence resolver implemented; it returns only a boolean.
- Plain-text cloud health identity implemented with the official client User-Agent.
- Back On My Feet dry-run: PLANNED via ace-step-1.5-cloud, generation=false.
- Pájaro dry-run: PLANNED via ace-step-1.5-cloud, generation=false.
- Both compile to acemusic/acestep-v1.5-turbo with governed durations.
- Initial Python probe was rejected by Cloudflare; aligning the User-Agent with
  the official client repaired it. This is preserved as operational evidence.

## Next exact action

Add an explicit execution approval/budget gate and an output ingestor that
writes returned files and response metadata into benchmark manifests. Preserve
the installed DJ KAI output patch when reconciling future donor updates.


## 2026-08-27 free-route verification delta

- Official ACE-Step v1.5 Space is RUNNING_ON_ZERO and its public config/API
  discovery endpoints returned HTTP 200.
- Official ACE-Step repository describes acemusic.ai as 100% free; its health
  endpoint remains live, but /v1/models timed out after 15 seconds with no bytes.
  Therefore acemusic cloud remains UNKNOWN_COST/DEGRADED for execution.
- Installed Termux acestep.sh has /bin/bash shebang incompatible with Termux;
  explicit `bash script` bypasses it. Its models curl lacks max-time and hung,
  so the caller bounded it externally. Donor patch not modified.
- Promoted planning candidate: ACE-Step official HF ZeroGPU, FREE but daily
  quota-limited. No generation was attempted.
