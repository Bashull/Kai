# Kai Control Plane Parallel Capability Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate five promoted parallel Kai capabilities into the Control Plane through a curated, non-destructive adapter layer with safe discovery, health probes and allowlisted invocation.

**Architecture:** Add `tools/kai_capability_integrations.py` as the only execution boundary for external capability runtimes. The Control Plane consumes normalized adapter records and never executes arbitrary registry artifacts. The capability registry remains authoritative for lifecycle state; package manifests define functional contract.

**Tech Stack:** Python 3.13 stdlib (`argparse`, `dataclasses`, `json`, `pathlib`, `subprocess`, `tomllib`), `unittest`, existing Kai memory and capability registry.

## Global Constraints

- Source before runtime.
- Snapshot before replace.
- TDD: prove RED before implementation and GREEN after.
- `shell=False` for subprocess execution.
- No secret propagation or discovery.
- No `storage-commander execute` in this phase.
- No arbitrary capability execution.
- No automatic `CANONICAL` promotion.
- Registry lifecycle state overrides stale package lifecycle claims.

---
### Task 1: Governed integration catalogue and discovery

**Files:**
- Create: `tools/kai_capability_integrations.py`
- Create: `tests/test_kai_capability_integrations.py`

**Interfaces:**
- Produces: `IntegrationSpec`, `CapabilityIntegrationManager`
- `CapabilityIntegrationManager.list_integrations() -> list[dict[str, Any]]`
- `CapabilityIntegrationManager.probe(slug: str) -> dict[str, Any]`
- `CapabilityIntegrationManager.invoke(slug: str, operation: str, args: list[str]) -> dict[str, Any]`

- [ ] **Step 1: Write failing discovery tests**

```python
manager = CapabilityIntegrationManager(capability_home=home)
records = {item["slug"]: item for item in manager.list_integrations()}
assert set(records) == {
    "storage-commander", "termux-bridge-planner", "backup-manifest",
    "file-indexer", "local-knowledge-vault",
}
assert records["backup-manifest"]["registry_state"] == "PROMOTED"
assert records["backup-manifest"]["available"] is True
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_kai_capability_integrations -v`
Expected: FAIL because `tools.kai_capability_integrations` does not exist.
- [ ] **Step 3: Implement the curated adapter catalogue**

```python
@dataclass(frozen=True)
class IntegrationSpec:
    slug: str
    module: str
    allowed_operations: tuple[str, ...]
    probe_args: tuple[str, ...]
    mutation_policy: str
    requires_live_transport: bool = False

INTEGRATIONS = {
    "storage-commander": IntegrationSpec(
        slug="storage-commander",
        module="kai_storage_commander.cli",
        allowed_operations=("plan",),
        probe_args=("--help",),
        mutation_policy="PLAN_ONLY",
        requires_live_transport=True,
    ),
}
```

Implement registry lookup by capability slug/provenance runtime path, package manifest loading, `pyproject.toml` script discovery and normalized warnings.

- [ ] **Step 4: Add allowlist and subprocess safety tests**

```python
with self.assertRaises(ValueError):
    manager.invoke("storage-commander", "execute", ["{}"])
result = manager.probe("backup-manifest")
self.assertIn(result["status"], {"HEALTHY", "DEGRADED", "BLOCKED_EXTERNAL"})
```
- [ ] **Step 5: Run GREEN and commit Task 1**

Run: `python -m unittest tests.test_kai_capability_integrations -v`
Expected: all Task 1 tests PASS.

Commit:
```bash
git add tools/kai_capability_integrations.py tests/test_kai_capability_integrations.py
git commit -m "feat: add governed capability integration manager"
```

### Task 2: Integrate discovery and health into Kai Control Plane

**Files:**
- Modify: `tools/kai_control_plane.py`
- Modify: `tests/test_kai_control_plane.py`

**Interfaces:**
- Consumes: `CapabilityIntegrationManager`
- Produces: `KaiControlPlane.integrations()`
- Produces: `KaiControlPlane.integration_doctor()`
- Produces: `KaiControlPlane.integration_call(slug, operation, args)`

- [ ] **Step 1: Write failing Control Plane tests**

```python
items = plane.integrations()
self.assertEqual({x["slug"] for x in items}, EXPECTED_INTEGRATIONS)
doctor = plane.integration_doctor()
self.assertEqual(doctor["required_count"], 5)
self.assertIn(doctor["status"], {"HEALTHY", "DEGRADED", "BLOCKED_EXTERNAL"})
```
- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_kai_control_plane.KaiControlPlaneTests -v`
Expected: FAIL because integration methods are absent.

- [ ] **Step 3: Implement Control Plane methods and doctor composition**

```python
def integrations(self) -> list[dict[str, Any]]:
    return self.integration_manager.list_integrations()

def integration_doctor(self) -> dict[str, Any]:
    return self.integration_manager.doctor()

def integration_call(self, slug: str, operation: str, args: list[str]) -> dict[str, Any]:
    return self.integration_manager.invoke(slug, operation, args)
```

Extend `doctor()` with an `integrations` block and make global status `DEGRADED` if a required promoted integration is missing or fails a non-external safe probe.

- [ ] **Step 4: Run GREEN and commit Task 2**

Run: `python -m unittest tests.test_kai_control_plane.KaiControlPlaneTests -v`
Expected: all Control Plane tests PASS.

Commit:
```bash
git add tools/kai_control_plane.py tests/test_kai_control_plane.py
git commit -m "feat: integrate promoted parallel capabilities into control plane"
```
### Task 3: CLI commands and deployed-runtime regression

**Files:**
- Modify: `tools/kai_control_plane.py`
- Modify: `tests/test_kai_control_plane_cli.py`
- Modify: `skills/kai-control-plane/SKILL.md`
- Modify: `tests/test_skill_contracts.py`

**Interfaces:**
- CLI commands: `integrations`, `integration-doctor`, `integration-call`
- Conversational aliases: `/integraciones`, `/doctor-integraciones`, `/usa-capacidad`

- [ ] **Step 1: Write failing CLI tests**

```python
result = self.run_cli("integrations")
self.assertEqual(result.returncode, 0, result.stderr)
payload = json.loads(result.stdout)
self.assertEqual({x["slug"] for x in payload}, EXPECTED_INTEGRATIONS)

result = self.run_cli("integration-call", "--name", "storage-commander", "--operation", "execute", "--")
self.assertNotEqual(result.returncode, 0)
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_kai_control_plane_cli -v`
Expected: FAIL because new CLI commands are absent.
- [ ] **Step 3: Implement CLI parsing and dispatch**

```python
sub.add_parser("integrations")
sub.add_parser("integration-doctor")
call = sub.add_parser("integration-call")
call.add_argument("--name", required=True)
call.add_argument("--operation", required=True)
call.add_argument("args", nargs=argparse.REMAINDER)
```

Dispatch through the existing `KaiControlPlane` methods only.
Update `COMMAND_ALIASES` and the `kai-control-plane` skill contract.

- [ ] **Step 4: Add deployed-runtime regression**

Copy `kai_control_plane.py`, `kai_location_policy.py` and `kai_capability_integrations.py` into a temporary isolated runtime folder and assert `--help` and `integrations` both exit 0.

- [ ] **Step 5: Run GREEN and commit Task 3**

Run:
`python -m unittest tests.test_kai_control_plane_cli tests.test_skill_contracts -v`
Expected: all tests PASS.

Commit:
```bash
git add tools/kai_control_plane.py tests/test_kai_control_plane_cli.py skills/kai-control-plane/SKILL.md tests/test_skill_contracts.py
git commit -m "feat: expose governed capability integrations in CLI"
```
### Task 4: Real runtime verification, deployment, evidence and memory

**Files:**
- Deploy: `agent_tools/kai_control_plane/kai_control_plane.py`
- Deploy: `agent_tools/kai_control_plane/kai_location_policy.py`
- Deploy: `agent_tools/kai_control_plane/kai_capability_integrations.py`
- Deploy: `skills/kai-control-plane/SKILL.md`
- Update evidence under `C:\Users\ASIER\.kai_capabilities\evidence\`
- Update memory under `C:\Users\ASIER\.kai_memory\`

- [ ] **Step 1: Run the full fresh suite**

Run: `python -m unittest discover -s tests -v`
Expected: 0 failures.

- [ ] **Step 2: Verify worktree state and commit any final regression-only changes**

Run: `git status --short && git log -5 --oneline`
Expected: no accidental generated files or untracked caches.

- [ ] **Step 3: Deploy only verified source files**

Copy source files to runtime without altering capability candidate packages.
Do not modify the five historical/promoted package manifests.

- [ ] **Step 4: Verify exact source/runtime SHA-256 parity**

Require exact matches for each deployed Control Plane integration file.
Write deterministic deployment evidence JSON.
- [ ] **Step 5: Run real integration doctor and safe probes**

Run runtime Control Plane against real `C:\Users\ASIER\.kai_memory` and `C:\Users\ASIER\.kai_capabilities`.
Expected:
- core doctor `HEALTHY`;
- five integrations discovered;
- no arbitrary execution path;
- live transport may report `BLOCKED_EXTERNAL` without misclassifying code health.

- [ ] **Step 6: Save durable memory and session closure**

Record:
- integrated capability IDs and versions;
- commits;
- test counts;
- deployment hashes;
- runtime doctor result;
- any blocked external dependencies;
- next governed action.

Regenerate boot packet and rerun doctor after session closure.

- [ ] **Step 7: Update Drive CURRENT sources only with verified facts**

Update the commands/storage contract, technical evidence report, long-term memory boot CURRENT and Drive master index.
Preserve historical incident text; append resolution and current integration state instead of rewriting history.

## Plan self-review

- Spec coverage: all discovery, authority, allowlist, probe, CLI, testing, deployment and memory requirements are mapped to tasks.
- Placeholder scan: no unresolved placeholders or incomplete implementation steps.
- Type consistency: `CapabilityIntegrationManager` is the single adapter boundary consumed by `KaiControlPlane`.
- Scope: focused on five already-promoted capabilities; no arbitrary execution or destructive mutations.
