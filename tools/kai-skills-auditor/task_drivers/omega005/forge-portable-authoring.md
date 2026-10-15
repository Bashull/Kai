# Portable Data authoring

Use this check for a copied dashboard or report skill. Reuse a provider already
verified for the current task.

1. Resolve the provider root two directories above the skill directory. Preserve
   its `skills/`, `shared/`, `scripts/`, `templates/`, `assets/`, manifest, and
   package metadata at the packaged relative paths. A flat skill folder cannot
   resolve this runtime. Explicit sibling auxiliaries may be required even when
   their skill entrypoints are not selected.
2. Verify the source bundle and selected lab's hash-bound receipt before executing
   helpers. Integrity covers bytes and scope; it does not authenticate a publisher,
   prove all dependency closure, or certify runtime behavior.
3. Use an available absolute Node executable accepted by the captured runtime's
   gate. Data1.0.11 accepts20.19+,22.12+, or a major above22; it rejects21.
   Do not install dependencies, change integrity manifests, or fall back to source
   compilation to conceal missing or altered prebuilt assets.
4. For an existing project, resolve component references with the provider's
   `scripts/data-app.mjs prepare --project-dir /absolute/app`. For a new project,
   run `scripts/prepare-data-app.mjs` with an explicit `--surface dashboard` or
   `--surface report`, the reviewed snapshot, and a new absolute output. Read the
   copied `AGENTS.md`; preserve the artifact identity when revising.
5. Follow that guide for the build. With `--separate-data`, serve or deliver the
   complete `dist` directory: `index.html`, the content-addressed JSON sidecar,
   and `data-app-build.json`. HTML alone is incomplete. For a standalone offline
   file, use the documented `export-offline` command on the verified split build.
   Never substitute empty data or relabel a split HTML as self-contained.
6. Inspect the requested output and report which calculation, source-scope,
   rendered, keyboard, and accessibility checks actually ran. A successful build,
   HTTP response, or static source inspection does not establish visual acceptance.

This candidate reuses captured private Data1.0.11 resources without installing or
registering a plugin, granting account access, or certifying another operating
system. Scheduling, publication, summaries, and exports through other services
retain their own instructions, tools, and authorization. Resolve a requested route
at that time; do not invent a replacement service or copy sibling entrypoints
merely to make a local check pass.
