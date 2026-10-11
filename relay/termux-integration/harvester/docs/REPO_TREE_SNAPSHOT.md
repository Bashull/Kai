# Six-donor structural inventory · 2026-10-11

Read via authenticated GitHub connector `git/trees/<default-branch>?recursive=1`. All six returned `truncated=false`. These are **repository tree snapshots**, not completed semantic read-throughs of all source bytes. The SHA is the returned **Git TREE SHA**, not necessarily a commit SHA. This is `VERIFIED_SCOPE_TREE`, not FULL_CODE_INGEST.

| Repository | Git tree SHA | Blob files counted | Selected areas |
|---|---|---:|---|
| siraht/ChatGPTExporter | `c5618b3cc06eeb5b273d3727fe8729071441f291` | 72 | src/ 29; tests/ 20; docs/ 5 |
| harris-ahmad/chatliberate | `7f63cbfe400d1d74c64510e1fd7d1463055ef313` | 42 | packages/ 13; apps/ 12; assets/ 8 |
| OwlCt/ChatGPT-Export | `ea52daa231c877fafce9d849b390a64fa03ca349` | 53 | reader/ 32; test/ 2; userscript |
| D1DX/chatgpt-helper | `7d316cb064786207759b8d692abe4506dab459e0` | 13 | content.js, popup.js, converters.js, vendor |
| sisodiabhumca/AI-Exporter | `a1f1090c47da9f3ed938bcef1e8729796afc5a4d` | 75 | extension/ 38; tools/ 9; store-listing/ 19 |
| pionxzh/chatgpt-exporter | `f530206fc52d12285a09c396cd943e44f3f9cb0a` | 128 | src/ 64; tests/ 27; browser-test skill |

Totals: **383 file entries** in the inspected repository trees. This does not mean all 383 contents were retrieved or their behavior tested. The sample includes targeted source, docs, manifests, issues already identified in chat and tests in selected modules.

## What still needs true total ingestion

Record for each file path: exact blob SHA, raw bytes, license/sensitivity, architectural role, call graph, trigger, inputs/outputs, failures/recovery, tests, transfer×3 and disposition. Read all commit histories and issue threads that modify contracts, compare with current KAI Devourer code and then run transplant tests. The container's GitHub DNS is unavailable; the GitHub connector permits bounded individual file reads. Do not invent a completed 383-file audit.
