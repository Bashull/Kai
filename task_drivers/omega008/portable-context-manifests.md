# Context package formats

Read before preparing a context plugin or changing its manifest. Keep the existing audience, definitions, sources and working instructions intact. Choose the requested format before validating the ZIP.

| Outcome | Manifest | Action |
| --- | --- | --- |
| New portable Agent Plugins package | Root `plugin.json`, declaring `https://agent-plugins.org/schemas/1.0.0/plugin.schema.json` | Discover skills in root `skills/`; omit Codex-only root fields such as `skills` and `interface`. |
| Existing approved Codex package or current Codex scaffold | `.codex-plugin/plugin.json` | Preserve its supported layout unless conversion was requested. Do not relabel it as Agent Plugins 1.0. |
| Explicit standalone skill | Its actual skill directory and references | Follow the host's skill contract; a plugin wrapper is unnecessary. |

For portable packages, put approved OpenAI settings under `extensions["com.openai"]`. When that value is an object, including `{}`, it supplies the entire OpenAI configuration; settings do not merge with the compatibility overlay. When it is absent, `.codex-plugin/plugin.json` can supply the fallback. The root manifest still determines portable identity and component discovery. Do not infer missing settings from an ignored overlay.

During an authorized conversion, preserve publisher, identity, sources, approved UI fields and referenced assets. Move applicable OpenAI settings together into their selected location. A format change does not authorize changing definitions, copying adjacent personal context, enabling apps, adding hooks or installing anything. Do not merely rename a Codex manifest: its field contract differs.

Reuse available authoring tools, identifying which format they produce. If they only scaffold Codex, retain that result for a Codex request or author the requested portable files directly. Check the selected manifest, local references, approved bytes and archive using the existing packaging checks. Distinguish a directed structural check from full schema validation, actual installation and observed agent behavior. Keep diffs and prior versions outside the distributable package.

Checked 2026-10-16: [OpenAI packaging](https://developers.openai.com/plugins/build/plugins), [Agent Plugins specification](https://agent-plugins.org/specification), and [manifest schema](https://agent-plugins.org/schemas/1.0.0/plugin.schema.json). Recheck the target's current contract before claiming a later installation or submission.
