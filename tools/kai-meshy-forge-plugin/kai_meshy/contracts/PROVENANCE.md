This package contains KAI's own restricted structural contracts, researched on
2026-10-18. It contains no vendor implementation code or executable downloaded
donor. The bundled catalogue records every source URL, byte length and SHA-256.
The vendor documentation's implementation licence is unknown; no licence grant
is inferred. Code licensing follows the enclosing KAI project.

The official OpenAPI snapshot supplied structural field types and bounds. The
individual endpoint pages supplied stage-specific fields, relationships and
Creative Lab / Text to Motion contracts absent from that snapshot. The pricing
page supplied credit rules. Descriptions/examples were removed when extracting
structure. The reproducible extraction script and unmodified source snapshots
are retained in the governed evidence repository and Drive archive.

The contract is a deliberately restricted documented subset. Local rejection of
unknown/null/ambiguous fields does not claim that Meshy's entire API rejects
them. A schema is not proof that a vendor operation was executed. These 35 POST
operations were tested offline; no generation or billable API request is part of
catalogue validation. GET list/get/cancel route metadata does not imply all
operation paths have been live-tested. Print Analyze is a stateful authenticated
POST despite its published zero-credit price.

`validate` returns the normalized request in memory for the existing engine.
It must never be logged or returned by a public MCP tool because references can
contain signed URLs or base64 media. `validation_report` is the public alternative.
`quote` reports a price gate only. `spend_allowed: true` never grants user approval,
account entitlement, write permission, credit reservation or spending authority.
The actual engine enforces those gates and the owner's NO_NEW_SPEND decision.

Context is caller-supplied evidence, never an authority grant. Before submission,
the engine must reconcile parent tasks with the real account, validate media,
check retention/geometry requirements and enforce human visual approval for every
Creative Lab build. Source media limits are conservative decimal-byte limits.
Public URL reachability/actual size and model geometry require the asset pipeline.
The catalogue hashes data URIs but does not pretend their bytes are valid models.

Prices are exact only for published and compatible configurations. Motion-task
retargeting has no published exact price and always returns UNKNOWN, denying the
pricing gate. High-resolution Text to 3D Refine without a resolved compatible
parent model also returns UNKNOWN. Credit prices are versioned documentary facts,
not a promise of future vendor pricing. Existing unknown POSTs must be reconciled
through the ledger; a quote is never permission to repeat a POST.

Pricing freshness is a KAI policy, not a vendor validity guarantee. The pinned
source was checked on2026-10-18UTC. Quotes expire on2026-10-25T00:00:00Z (at most
seven days); the vendor can change prices sooner. Stale quotes return UNKNOWN,
null payable credits and a denied price gate while retaining documentary_credits
as a historical estimate. The current UTC date is used by default. `as_of` is an
offline testing/planning argument and must not be exposed as a client override
for submissions. Refresh evidence and version the catalogue before spending with
an expired snapshot. The engine must compare the catalogue hash at submission.

Notable reconciliations: generation `latest` is pinned to Meshy7.1; Retexture
`latest` is pinned to Meshy7. Smart Topology defaults to T2.5 following the
2026-10-15 changelog and has triangle-only model-specific face-count bounds.
Lowpoly is deprecated and is rejected on/after2026-10-30. Text Refine preserves
model inheritance when no explicit model is supplied. OpenAPI's broad fused/count
union, undocumented experimental fields and ambiguous legacy Remesh resize/convert
shortcuts are excluded. Meshy5 was retired. The individually documented
`motion_task_id` field is supported structurally despite its OpenAPI omission.

`CapabilityCatalog(path=None)` loads the package-local catalogue. `list` returns
summaries; `describe(id)` returns routes, typed request schema (`input_contract`),
input-field roles, prices, sources and preconditions. `validate(id, parameters,
context=None, as_of=None)` returns normalized parameters or a sanitized
`ContractError` (`ForgeError`). `validation_report` returns only validity, field
names, warnings and a content fingerprint. `quote` returns integer credits or
UNKNOWN, a price-source receipt, fingerprint and explicit authorization disclaimer.
No method makes an HTTP call or mutates the ledger.
