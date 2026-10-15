# Check the edition before document export

Use the existing compiled app, its reviewed snapshot and the requested view. Keep the app unchanged during conversion. Do not reconcile a mismatch by silently refreshing data or rebuilding.

For a local `separate-data-v1` build, retain the complete `dist` bundle: HTML, content-addressed snapshot and build manifest. From a provider-relative staged copy, use the compatible Node executable and the absolute path to `scripts/verify-local-export.mjs` in this skill, with `--project-dir /absolute/existing-project`. It reuses the provider's split verifier and compares the current `src/data.json` fingerprint with that compiled edition. A mismatch, missing resource or altered sidecar blocks conversion. The helper is read-only and supports only this split layout; it does not reject other layouts on behalf of a separate verified workflow.

A successful fingerprint check establishes byte coherence at that moment. It does not verify the selected presentation, rendered text, hidden components, chart selection, claim accuracy, document quality or authenticity of the publisher. For an inline build, follow the current app contract and verify its embedded evidence independently; do not rebuild merely to fit this helper.

Resolve the requested view from verified saved presentation or the available source page. If the user explicitly requests the project's default view, state that scope in the conversion record. Unknown browser-only edits are not an empty presentation. Include reader-facing collapsed methods/evidence/follow-up content, while excluding hidden components and action controls. If a material part of the requested view cannot be established, retain the source and report the missing evidence.

Read the current canonical Documents skill before authoring. A Data support pack does not include that skill, its authoring libraries, fonts or renderer. Confirm those capabilities in the actual host. Resolve a requested preset from the available authoring system; do not claim a named preset was applied when it is unavailable. Use an authorized neutral design when the task supplies that direction.

Preserve exact claims, signs, units, definitions, synthetic labels, evidence cutoff, source labels and meaningful links. Keep text and tables native/editable; retain proper heading order and real repeating table headers. For existing charts, follow the captured image priority; native tables do not authorize reconstructing charts. Record whether images were present and which paths were exercised.

Render the DOCX with the canonical renderer and inspect every page. Run the supported structural accessibility checks, recording their limits; they are not complete assistive-technology or WCAG certification. Keep title, note, caveats and provenance in the actual document. Native Google Docs delivery follows the current canonical Documents import contract. A local DOCX, a successful upload, or an unavailable import does not establish native Google Docs delivery. Retain a verified local DOCX if native delivery is blocked.

Record source fingerprints before/after, output hash, page count, content checks, view scope, structural accessibility findings, and destination readback when applicable. Keep QA images internal unless explicitly requested. Do not add a new service, installer or provider dependency to perform this check.
