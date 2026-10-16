# Existing Data app to slides

Use the existing compiled app directly. Preserve its reviewed evidence and the explicitly requested presentation; do not rebuild the app or create an intermediate report.

## Edition and view

For split-data-v1 local output, reuse the existing read-only helper from the document export family:

```bash
node ../convert-to-doc/scripts/verify-local-export.mjs --project-dir /absolute/project
```

Resolve that relative path from this skill directory. The portable catalog binds the helper as one explicit sibling auxiliary; it does not select the document skill's entrypoint. Keep the complete verified dist bundle, including manifest and sidecar. A source/build mismatch blocks conversion, without implicit repair. The helper validates exact bytes and the existing provider's split contract; it does not establish browser state, semantic truth or authoring quality. It only supports split-data-v1. For inline/hosted layouts follow their contracts; do not interpret unsupported layout as empty data.

Establish the requested view separately. If the task explicitly requests project defaults, inspect source defaults and the verified compiled reader copy; include reader-facing folded methods and disclose the browser inspection scope. If filters, selected chart states or browser edits are unknown and matter to the request, resolve them before authoring. Hash snapshots are not an atomic guarantee against later concurrent edits.

## Canonical presentation authoring

Read the actual current canonical Presentations skill, runtime implementation, editable evidence and finalization references before authoring. Use its supported bundled Artifact Tool API and required marker/finalizer; do not infer compatibility from an older export recipe. Resolve template/style through its current policy, honoring explicit neutral style without an unnecessary template question. This private pack does not include Presentations or its runtime, fonts, renderer or native import provider.

Keep all required source text, titles, caveats, units, signed values, grain, sources and evidence cutoff. Do not invent a recommendation or summary. Native report tables must remain native editable tables; chart PNGs follow the shared capture contract. Do not turn a table or an entire page into an image to satisfy layout checks. Supplemental data/provenance may be in an editable appendix when needed; retain the distinction between fictional fixture and observed production data.

Finalize the PPTX with the canonical package/layout/font/import checks and the appropriate declared native-table requirements. Render every final slide and inspect it individually at full size. Check content coverage against the source as a separate step: a structural pass does not prove factual preservation or visual quality. Keep QA images and any intermediate PDF internal; do not include them as requested deliverables. Record any repaired attempt and the final artifact hash. A local import check is not Microsoft PowerPoint UI or native Google Slides verification.

## Destination

A verified local PPTX meets a request for that format. For a new native Google Slides deck, use the current canonical local-PPTX → native import route and inspect the destination. If that route is absent or fails, explain the blocker and ask about an alternative; do not silently switch to image insertion or deliver an unrequested PPTX. A native insertion workflow is allowed only when explicitly requested and supported by the current canonical route. A successful upload alone proves neither editability nor preserved design. Retain the source project and original chart images unchanged.
