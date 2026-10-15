# Portable authoring runtime

Apply this check to a copied or selectively staged dashboard skill. Use the
existing installed plugin when it has already been verified for the task.

1. Resolve the provider root two directories above this skill directory. Keep
   `skills/build-dashboard/`, `shared/`, `scripts/`, `templates/`, `assets/`,
   `.codex-plugin/plugin.json`, and the package metadata at their packaged relative
   locations. A flat copy of this skill cannot resolve the shared runtime.
2. Verify the source bundle and the selected lab's hash-bound file receipt before
   executing its helpers. The Forge toolkit's integrity and rollback checks cover
   packaged bytes; they do not prove provenance safety, runtime behavior, or all
   transitive dependencies. Never execute a helper solely because its name matches.
3. Use an available absolute Node executable compatible with the captured runtime.
   This capture requires Node 20.19+ or 22.12+ (or a higher major than 22); check the
   actual runtime gate rather than assuming every Node installation qualifies.
   Do not install dependencies or fall back to a source build to conceal a missing
   or damaged prebuilt runtime.
4. Run the provider's `scripts/data-app.mjs prepare --project-dir /absolute/app`
   to resolve the component reference for an existing project. For a new project,
   use `scripts/prepare-data-app.mjs` with the focused skill's reviewed snapshot and
   a new absolute destination, then read its copied `AGENTS.md`. Run outside active
   skill roots. Preserve the returned artifact identity and the input snapshot.
5. Build with the verified provider's absolute `scripts/data-app.mjs` path and the
   copied authoring guide. A split build needs its complete `dist` directory, not
   only `index.html`. An offline export is a distinct supported command; do not
   silently relabel a split build as a standalone file.

This private candidate restores the captured offline authoring resources from
Data 1.0.11. It does not install or register the plugin, establish account access,
or certify another operating system. The shared dependency policy's manifest is
discovery metadata, not an authorization or successful connection receipt.

Scheduling, publishing, summary delivery, and other conditional routes may require
sibling skills, host actions, credentials handled by authorized tools, and remote
services. If a route is requested, resolve that route's own instructions and actual
tools at that time. A dashboard-only selective copy does not include sibling skill
trees. Report the specific missing route without inventing a replacement service
or claiming the entire dashboard capability passed.
