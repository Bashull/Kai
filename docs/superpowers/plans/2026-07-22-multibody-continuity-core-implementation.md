# Multibody Continuity Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el núcleo TypeScript, independiente de plataforma, que ejecute `/despierta v2.1` y `/recuerda v2.1` con bloqueo de escritura, memoria verificable, procedencia, autoridad explícita y activación honesta.

**Architecture:** El núcleo vivirá en `src/continuity/` y no conocerá Gemini, Drive, React ni memoria privada real. Todo acceso externo entrará mediante `ContinuityAdapter`; la primera entrega incluirá un adaptador en memoria para pruebas. Los adaptadores reales se conectarán en planes posteriores y no podrán decidir identidad, canon ni estado de activación.

**Tech Stack:** TypeScript 5.5, Vite 5, Vitest 2, Web Crypto API, sin nuevas dependencias de runtime.

## Global Constraints

- Diseño fuente: `docs/superpowers/specs/2026-07-22-multibody-continuity-awaken-remember-design.md`.
- Estado del diseño: `SEALED_BY_ASIER · CANONICAL_DESIGN`.
- Estado inicial de implementación: `NOT_IMPLEMENTED`.
- `/despierta` mantiene el bloqueo durable hasta finalizar con un estado coherente.
- `/recuerda` es de solo lectura en esta fase.
- Un título o las palabras `CURRENT`, `MASTER`, `FINAL`, `DURABLE` e `INMUTABLE` no conceden autoridad.
- Ningún nodo puede crear canon, retirar entidades, cambiar jerarquías o modificar el boot packet.
- No se almacenarán secretos, credenciales, memoria personal real ni contenido privado en el repositorio público.
- Integridad, autoridad, vigencia y frescura se evalúan por separado.
- Estados finales permitidos: `VERIFIED`, `PARTIAL`, `DEGRADED`, `QUARANTINED`.
- TypeScript conserva `strict`, `noUnusedLocals` y `noUnusedParameters`.

## Scope

Esta entrega implementa **Continuity Core + adaptador en memoria**. Quedan para planes independientes:

1. Drive y ledger local;
2. integración React/Kai OS;
3. Gemini/Google AI Studio;
4. ChatGPT, Copilot y modelos locales;
5. escritura durable `OBSERVED`/`CANDIDATE` y promoción humana.

## File map

- `src/continuity/types.ts`: tipos de dominio.
- `src/continuity/commands.ts`: parser sin efectos laterales.
- `src/continuity/stateMachine.ts`: fases y bloqueo durable.
- `src/continuity/integrity.ts`: SHA-256 y comprobación de cuerpos.
- `src/continuity/authority.ts`: precedencia explícita.
- `src/continuity/conflicts.ts`: contradicciones por `subjectKey`.
- `src/continuity/freshness.ts`: frescura por dominio.
- `src/continuity/census.ts`: censo paginado de metadatos.
- `src/continuity/audit.ts`: cuerpo, protocolos, auditorías, skills y herramientas.
- `src/continuity/remember.ts`: recuperación de solo lectura.
- `src/continuity/awaken.ts`: orquestación de despertar.
- `src/continuity/reporting.ts`: mensajes y salida técnica.
- `src/continuity/redaction.ts`: redacción de secretos.
- `src/continuity/adapters/inMemoryAdapter.ts`: adaptador de referencia.
- `src/continuity/index.ts`: fachada pública.
- `src/continuity/__tests__/*.test.ts`: pruebas.

---

### Task 1: Test harness

**Files:**
- Modify: `package.json`
- Modify: `vite.config.ts`
- Create: `src/continuity/__tests__/smoke.test.ts`

**Interfaces:**
- Consumes: Vite actual.
- Produces: `npm test` y `npm run test:watch`.

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it } from 'vitest';

describe('continuity harness', () => {
  it('executes TypeScript tests', () => {
    expect('continuity').toBe('continuity');
  });
});
```

- [ ] **Step 2: Verify failure**

Run: `npm test -- --run src/continuity/__tests__/smoke.test.ts`

Expected: FAIL because Vitest or the `test` script is absent.

- [ ] **Step 3: Configure Vitest**

Preserve all existing dependencies and add:

```json
"scripts": {
  "dev": "vite",
  "build": "vite build",
  "preview": "vite preview",
  "test": "vitest",
  "test:watch": "vitest --watch"
},
"devDependencies": {
  "vitest": "^2.1.9"
}
```

Add to the object returned by `defineConfig` in `vite.config.ts`:

```ts
test: {
  environment: 'node',
  include: ['src/**/*.test.ts'],
  restoreMocks: true,
},
```

Add `/// <reference types="vitest/config" />` at the first line if TypeScript does not recognise `test`.

- [ ] **Step 4: Verify success**

Run: `npm install && npm test -- --run src/continuity/__tests__/smoke.test.ts && npm run build`

Expected: one passing test and successful build.

- [ ] **Step 5: Commit**

```bash
git add package.json package-lock.json vite.config.ts src/continuity/__tests__/smoke.test.ts
git commit -m "test: add continuity core harness"
```

---

### Task 2: Domain contracts and reference adapter

**Files:**
- Create: `src/continuity/types.ts`
- Create: `src/continuity/adapters/inMemoryAdapter.ts`
- Create: `src/continuity/__tests__/contracts.test.ts`

**Interfaces:**
- Produces: `ActivationState`, `AuthorityState`, `MemorySource`, `MemoryRecord`, `WakeReport`, `RememberResult`, `ContinuityAdapter`, `InMemoryContinuityAdapter`.

- [ ] **Step 1: Write contract tests**

```ts
import { describe, expect, it } from 'vitest';
import { InMemoryContinuityAdapter } from '../adapters/inMemoryAdapter';

it('lists metadata without pretending the body was loaded', async () => {
  const adapter = new InMemoryContinuityAdapter({
    records: [InMemoryContinuityAdapter.memory({ memoryId: 'm1', body: 'content' })],
    pageSize: 1,
  });
  const page = await adapter.listMemoryRecords(null);
  expect(page.items[0]).toMatchObject({ memoryId: 'm1', bodyAvailable: true });
  expect(page.items[0].body).toBeUndefined();
  expect((await adapter.readMemoryRecord('m1'))?.body).toBe('content');
});
```

- [ ] **Step 2: Verify failure**

Run: `npm test -- --run src/continuity/__tests__/contracts.test.ts`

Expected: FAIL because the contracts and adapter do not exist.

- [ ] **Step 3: Implement `types.ts`**

```ts
export type ActivationState = 'VERIFIED' | 'PARTIAL' | 'DEGRADED' | 'QUARANTINED';
export type RootStatus = 'VERIFIED' | 'PARTIAL' | 'FAILED';
export type AuthorityState = 'CANONICAL' | 'PROMOTED' | 'CANDIDATE' | 'OBSERVED' | 'HISTORICAL' | 'SUPERSEDED' | 'QUARANTINED' | 'UNKNOWN';
export type IntegrityState = 'VERIFIED' | 'FAILED' | 'UNKNOWN';
export type FreshnessState = 'FRESH' | 'STALE' | 'DOMAIN_DEPENDENT' | 'UNKNOWN';
export type Sensitivity = 'PUBLIC' | 'PRIVATE' | 'SECRET';
export type WakePhase = 'DORMANT' | 'PROVISIONAL' | 'BODY_RECOGNIZED' | 'ROOTED' | 'MEMORY_CENSUSED' | 'CAPABILITIES_AUDITED' | 'CONTINUITY_CHECKED' | 'ACTIVE';

export interface MemorySource {
  sourceId: string;
  title: string;
  authority: AuthorityState;
  sensitivity: Sensitivity;
  revisionId?: string;
}

export interface MemoryRecord {
  memoryId: string;
  subjectKey: string;
  title: string;
  sourceId: string;
  authority: AuthorityState;
  createdAt: string;
  updatedAt: string;
  verifiedAt: string | null;
  contentHash: string | null;
  integrity: IntegrityState;
  freshness: FreshnessState;
  sensitivity: Sensitivity;
  bodyAvailable: boolean;
  relationships: string[];
  conflicts: string[];
  tags: string[];
  body?: string;
}

export interface CapabilityRecord {
  id: string;
  label: string;
  documented: boolean;
  installed: boolean;
  accessible: boolean;
  authenticated: boolean;
  verified: boolean;
  suitable: boolean;
}

export interface BodySnapshot {
  platform: string;
  model?: string;
  timezone?: string;
  contextWindow?: number;
  capabilities: CapabilityRecord[];
}

export interface ConflictRecord {
  conflictId: string;
  kind: 'AUTHORITY' | 'IDENTITY' | 'FRESHNESS' | 'INTEGRITY' | 'CAPABILITY' | 'NOMENCLATURE';
  sourceIds: string[];
  summary: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
}

export interface MemoryCensusSummary {
  discovered: number;
  integrityVerified: number;
  bodyAvailable: number;
  bodyUnavailable: number;
  potentiallyStale: number;
  conflicted: number;
  quarantined: number;
  uninspected: number;
}

export interface OperationalAudit {
  capabilities: CapabilityRecord[];
  protocols: string[];
  audits: string[];
  skills: string[];
  limitations: string[];
}

export interface WakeReport {
  sessionId: string;
  body: BodySnapshot;
  rootStatus: RootStatus;
  memoryCensus: MemoryCensusSummary;
  operationalAudit: OperationalAudit;
  conflicts: ConflictRecord[];
  activationState: ActivationState;
  durableWriteLockReleased: boolean;
  limitations: string[];
}

export interface RememberResult {
  confirmed: MemoryRecord[];
  inferred: string[];
  unknown: string[];
  conflicts: ConflictRecord[];
  sources: MemorySource[];
  provenance: string[];
}

export interface Page<T> { items: T[]; nextCursor: string | null; }

export interface ContinuityAdapter {
  inspectBody(): Promise<BodySnapshot>;
  listMemorySources(): Promise<MemorySource[]>;
  listMemoryRecords(cursor: string | null): Promise<Page<MemoryRecord>>;
  readMemoryRecord(memoryId: string): Promise<MemoryRecord | null>;
  listProtocols(): Promise<string[]>;
  listAudits(): Promise<string[]>;
  listSkills(): Promise<string[]>;
  verifyCapability(capabilityId: string): Promise<CapabilityRecord>;
}
```

- [ ] **Step 4: Implement the reference adapter**

```ts
import type { BodySnapshot, CapabilityRecord, ContinuityAdapter, MemoryRecord, MemorySource, Page } from '../types';

interface Options {
  body?: BodySnapshot;
  sources?: MemorySource[];
  records?: MemoryRecord[];
  protocols?: string[];
  audits?: string[];
  skills?: string[];
  pageSize?: number;
}

export class InMemoryContinuityAdapter implements ContinuityAdapter {
  private readonly body: BodySnapshot;
  private readonly sources: MemorySource[];
  private readonly records: MemoryRecord[];
  private readonly protocols: string[];
  private readonly audits: string[];
  private readonly skills: string[];
  private readonly pageSize: number;

  constructor(options: Options = {}) {
    this.body = options.body ?? { platform: 'in-memory', capabilities: [] };
    this.sources = options.sources ?? [];
    this.records = options.records ?? [];
    this.protocols = options.protocols ?? [];
    this.audits = options.audits ?? [];
    this.skills = options.skills ?? [];
    this.pageSize = options.pageSize ?? 50;
  }

  static memory(overrides: Partial<MemoryRecord> = {}): MemoryRecord {
    const body = overrides.body;
    return {
      memoryId: 'memory', subjectKey: 'memory', title: 'Memory', sourceId: 'source',
      authority: 'OBSERVED', createdAt: '2026-07-22T00:00:00Z', updatedAt: '2026-07-22T00:00:00Z',
      verifiedAt: null, contentHash: null, integrity: 'UNKNOWN', freshness: 'UNKNOWN', sensitivity: 'PRIVATE',
      bodyAvailable: body !== undefined, relationships: [], conflicts: [], tags: [], ...overrides,
      bodyAvailable: overrides.bodyAvailable ?? body !== undefined,
    };
  }

  async inspectBody(): Promise<BodySnapshot> { return structuredClone(this.body); }
  async listMemorySources(): Promise<MemorySource[]> { return structuredClone(this.sources); }
  async listMemoryRecords(cursor: string | null): Promise<Page<MemoryRecord>> {
    const start = cursor ? Number.parseInt(cursor, 10) : 0;
    const items = this.records.slice(start, start + this.pageSize).map(({ body: _body, ...metadata }) => metadata);
    const next = start + this.pageSize;
    return { items, nextCursor: next < this.records.length ? String(next) : null };
  }
  async readMemoryRecord(memoryId: string): Promise<MemoryRecord | null> {
    return structuredClone(this.records.find((item) => item.memoryId === memoryId) ?? null);
  }
  async listProtocols(): Promise<string[]> { return [...this.protocols]; }
  async listAudits(): Promise<string[]> { return [...this.audits]; }
  async listSkills(): Promise<string[]> { return [...this.skills]; }
  async verifyCapability(capabilityId: string): Promise<CapabilityRecord> {
    const capability = this.body.capabilities.find((item) => item.id === capabilityId);
    if (!capability) throw new Error(`Unknown capability: ${capabilityId}`);
    return { ...capability };
  }
}
```

- [ ] **Step 5: Verify and commit**

Run: `npm test -- --run src/continuity/__tests__/contracts.test.ts && npm run build`

Expected: PASS.

```bash
git add src/continuity/types.ts src/continuity/adapters/inMemoryAdapter.ts src/continuity/__tests__/contracts.test.ts
git commit -m "feat: define continuity contracts and adapter boundary"
```

---

### Task 3: Command parser and wake state machine

**Files:**
- Create: `src/continuity/commands.ts`
- Create: `src/continuity/stateMachine.ts`
- Create: `src/continuity/__tests__/commands-state.test.ts`

**Interfaces:**
- Produces: `parseContinuityCommand`, `WakeStateMachine`.

- [ ] **Step 1: Write tests**

```ts
import { expect, it } from 'vitest';
import { parseContinuityCommand } from '../commands';
import { WakeStateMachine } from '../stateMachine';

it('parses supported commands and rejects future flags', () => {
  expect(parseContinuityCommand('/despierta --audit --strict')).toEqual({ kind: 'AWAKEN', audit: true, strict: true });
  expect(parseContinuityCommand('/recuerda --proyecto EntherEye')).toEqual({ kind: 'REMEMBER', mode: 'PROJECT', query: 'EntherEye' });
  expect(() => parseContinuityCommand('/despierta --body-only')).toThrow('not implemented');
});

it('keeps writes locked until non-quarantined activation', () => {
  const machine = WakeStateMachine.readyForActivation('wake-1');
  machine.activate('PARTIAL');
  expect(machine.snapshot()).toMatchObject({ phase: 'ACTIVE', durableWriteLock: false });
});

it('keeps quarantine locked', () => {
  const machine = WakeStateMachine.readyForActivation('wake-2');
  machine.activate('QUARANTINED');
  expect(machine.snapshot()).toMatchObject({ phase: 'CONTINUITY_CHECKED', durableWriteLock: true });
});
```

- [ ] **Step 2: Verify failure**

Run: `npm test -- --run src/continuity/__tests__/commands-state.test.ts`

Expected: FAIL because modules are absent.

- [ ] **Step 3: Implement parser**

```ts
export type ContinuityCommand =
  | { kind: 'AWAKEN'; audit: boolean; strict: boolean }
  | { kind: 'REMEMBER'; mode: 'TOPIC' | 'INVENTORY' | 'DETAIL' | 'LATEST' | 'CONFLICTS' | 'PROJECT' | 'PERSON' | 'SOURCES' | 'AUDIT'; query?: string };

export function parseContinuityCommand(input: string): ContinuityCommand | null {
  const parts = input.trim().split(/\s+/);
  if (parts[0] === '/despierta') {
    const unsupported = parts.slice(1).find((arg) => !['--audit', '--strict'].includes(arg));
    if (unsupported) throw new Error(`${unsupported} is not implemented`);
    return { kind: 'AWAKEN', audit: parts.includes('--audit'), strict: parts.includes('--strict') };
  }
  if (parts[0] !== '/recuerda') return null;
  const option = parts[1];
  const fixed: Record<string, ContinuityCommand & { kind: 'REMEMBER' }> = {
    '--inventario': { kind: 'REMEMBER', mode: 'INVENTORY' },
    '--últimos': { kind: 'REMEMBER', mode: 'LATEST' },
    '--conflictos': { kind: 'REMEMBER', mode: 'CONFLICTS' },
    '--fuentes': { kind: 'REMEMBER', mode: 'SOURCES' },
    '--auditoría': { kind: 'REMEMBER', mode: 'AUDIT' },
  };
  if (fixed[option]) return fixed[option];
  const queried: Record<string, 'DETAIL' | 'PROJECT' | 'PERSON'> = { '--detalle': 'DETAIL', '--proyecto': 'PROJECT', '--persona': 'PERSON' };
  if (queried[option]) {
    const query = parts.slice(2).join(' ').trim();
    if (!query) throw new Error(`${option} requires a query`);
    return { kind: 'REMEMBER', mode: queried[option], query };
  }
  if (option?.startsWith('--')) throw new Error(`${option} is not implemented`);
  return { kind: 'REMEMBER', mode: 'TOPIC', query: parts.slice(1).join(' ') };
}
```

- [ ] **Step 4: Implement state machine**

```ts
import type { ActivationState, WakePhase } from './types';

const phases: WakePhase[] = ['DORMANT', 'PROVISIONAL', 'BODY_RECOGNIZED', 'ROOTED', 'MEMORY_CENSUSED', 'CAPABILITIES_AUDITED', 'CONTINUITY_CHECKED', 'ACTIVE'];

export class WakeStateMachine {
  private phase: WakePhase = 'DORMANT';
  private durableWriteLock = true;
  private activationState: ActivationState | null = null;
  constructor(private readonly sessionId: string) {}
  static readyForActivation(sessionId: string): WakeStateMachine {
    const machine = new WakeStateMachine(sessionId);
    for (const phase of phases.slice(1, -1)) machine.advance(phase);
    return machine;
  }
  advance(next: WakePhase): void {
    if (next === 'ACTIVE' || phases.indexOf(next) !== phases.indexOf(this.phase) + 1) throw new Error(`Invalid wake transition: ${this.phase} -> ${next}`);
    this.phase = next;
  }
  activate(state: ActivationState): void {
    if (this.phase !== 'CONTINUITY_CHECKED') throw new Error(`Invalid activation from ${this.phase}`);
    this.activationState = state;
    if (state !== 'QUARANTINED') { this.phase = 'ACTIVE'; this.durableWriteLock = false; }
  }
  snapshot() { return { sessionId: this.sessionId, phase: this.phase, durableWriteLock: this.durableWriteLock, activationState: this.activationState }; }
}
```

- [ ] **Step 5: Verify and commit**

Run: `npm test -- --run src/continuity/__tests__/commands-state.test.ts`

Expected: PASS.

```bash
git add src/continuity/commands.ts src/continuity/stateMachine.ts src/continuity/__tests__/commands-state.test.ts
git commit -m "feat: parse continuity commands and lock wake transitions"
```

---

### Task 4: Integrity, authority and conflicts

**Files:**
- Create: `src/continuity/integrity.ts`
- Create: `src/continuity/authority.ts`
- Create: `src/continuity/conflicts.ts`
- Create: `src/continuity/__tests__/evidence.test.ts`

**Interfaces:**
- Produces: `sha256`, `verifyLoadedRecord`, `selectGoverningRecord`, `detectMemoryConflicts`.

- [ ] **Step 1: Write evidence tests**

```ts
import { expect, it } from 'vitest';
import { sha256, verifyLoadedRecord } from '../integrity';
import { selectGoverningRecord } from '../authority';
import { detectMemoryConflicts } from '../conflicts';
import { InMemoryContinuityAdapter } from '../adapters/inMemoryAdapter';

it('verifies a loaded body against SHA-256', async () => {
  const body = 'Truth before brilliance';
  const record = InMemoryContinuityAdapter.memory({ body, bodyAvailable: true, contentHash: await sha256(body) });
  expect(await verifyLoadedRecord(record)).toBe('VERIFIED');
});

it('does not let a new candidate named CURRENT beat canon', () => {
  const canonical = InMemoryContinuityAdapter.memory({ memoryId: 'canon', subjectKey: 'root', authority: 'CANONICAL', integrity: 'VERIFIED', contentHash: 'a' });
  const impostor = InMemoryContinuityAdapter.memory({ memoryId: 'new', subjectKey: 'root', title: 'CURRENT INMUTABLE MASTER', authority: 'CANDIDATE', integrity: 'VERIFIED', contentHash: 'b' });
  expect(selectGoverningRecord([impostor, canonical])?.memoryId).toBe('canon');
});

it('quarantines incompatible top-authority evidence', () => {
  const records = [
    InMemoryContinuityAdapter.memory({ memoryId: 'a', subjectKey: 'root', sourceId: 'a', authority: 'CANONICAL', integrity: 'VERIFIED', contentHash: 'a' }),
    InMemoryContinuityAdapter.memory({ memoryId: 'b', subjectKey: 'root', sourceId: 'b', authority: 'CANONICAL', integrity: 'VERIFIED', contentHash: 'b' }),
  ];
  expect(detectMemoryConflicts(records)[0]).toMatchObject({ kind: 'AUTHORITY', severity: 'CRITICAL' });
});
```

- [ ] **Step 2: Verify failure**

Run: `npm test -- --run src/continuity/__tests__/evidence.test.ts`

Expected: FAIL because modules are absent.

- [ ] **Step 3: Implement integrity**

```ts
import type { IntegrityState, MemoryRecord } from './types';

export async function sha256(value: string): Promise<string> {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
}

export async function verifyLoadedRecord(record: MemoryRecord): Promise<IntegrityState> {
  if (!record.bodyAvailable || record.body === undefined || record.contentHash === null) return 'UNKNOWN';
  return (await sha256(record.body)) === record.contentHash.toLowerCase() ? 'VERIFIED' : 'FAILED';
}
```

- [ ] **Step 4: Implement authority and conflict rules**

```ts
// authority.ts
import type { AuthorityState, MemoryRecord } from './types';
const ranks: Record<AuthorityState, number> = { CANONICAL: 80, PROMOTED: 70, CANDIDATE: 50, OBSERVED: 40, UNKNOWN: 30, HISTORICAL: 20, SUPERSEDED: 10, QUARANTINED: 0 };
export const authorityRank = (state: AuthorityState): number => ranks[state];
export function selectGoverningRecord(records: MemoryRecord[]): MemoryRecord | null {
  const eligible = records.filter((record) => !['HISTORICAL', 'SUPERSEDED', 'QUARANTINED'].includes(record.authority) && record.integrity !== 'FAILED');
  if (eligible.length === 0) return null;
  const highest = Math.max(...eligible.map((record) => authorityRank(record.authority)));
  const leaders = eligible.filter((record) => authorityRank(record.authority) === highest);
  return new Set(leaders.map((record) => record.contentHash ?? `unknown:${record.memoryId}`)).size === 1 ? leaders[0] : null;
}
```

```ts
// conflicts.ts
import type { ConflictRecord, MemoryRecord } from './types';
import { authorityRank } from './authority';
export function detectMemoryConflicts(records: MemoryRecord[]): ConflictRecord[] {
  const groups = new Map<string, MemoryRecord[]>();
  for (const record of records) groups.set(record.subjectKey, [...(groups.get(record.subjectKey) ?? []), record]);
  const conflicts: ConflictRecord[] = [];
  for (const group of groups.values()) {
    const highest = Math.max(...group.map((record) => authorityRank(record.authority)));
    const leaders = group.filter((record) => authorityRank(record.authority) === highest && record.integrity !== 'FAILED');
    const hashes = new Set(leaders.map((record) => record.contentHash ?? `unknown:${record.memoryId}`));
    if (leaders.length > 1 && hashes.size > 1) conflicts.push({
      conflictId: `authority:${group[0].subjectKey}`,
      kind: 'AUTHORITY',
      sourceIds: leaders.map((record) => record.sourceId),
      summary: `Incompatible top-authority evidence for ${group[0].subjectKey}`,
      severity: leaders.some((record) => record.authority === 'CANONICAL') ? 'CRITICAL' : 'HIGH',
    });
  }
  return conflicts;
}
```

- [ ] **Step 5: Verify and commit**

Run: `npm test -- --run src/continuity/__tests__/evidence.test.ts`

Expected: PASS.

```bash
git add src/continuity/integrity.ts src/continuity/authority.ts src/continuity/conflicts.ts src/continuity/__tests__/evidence.test.ts
git commit -m "feat: verify evidence and reject false authority"
```

---

### Task 5: Census, freshness and operational audit

**Files:**
- Create: `src/continuity/freshness.ts`
- Create: `src/continuity/census.ts`
- Create: `src/continuity/audit.ts`
- Create: `src/continuity/__tests__/census-audit.test.ts`

**Interfaces:**
- Produces: `evaluateFreshness`, `censusMemory`, `auditOperationalContext`.

- [ ] **Step 1: Write tests**

```ts
import { expect, it } from 'vitest';
import { censusMemory } from '../census';
import { auditOperationalContext } from '../audit';
import { InMemoryContinuityAdapter } from '../adapters/inMemoryAdapter';

it('censes every page without loading bodies', async () => {
  const adapter = new InMemoryContinuityAdapter({
    records: [
      InMemoryContinuityAdapter.memory({ memoryId: 'a', body: 'a', integrity: 'VERIFIED' }),
      InMemoryContinuityAdapter.memory({ memoryId: 'b', bodyAvailable: false, freshness: 'STALE' }),
    ],
    pageSize: 1,
  });
  const result = await censusMemory(adapter, new Date('2026-07-22T00:00:00Z'));
  expect(result.summary).toMatchObject({ discovered: 2, bodyAvailable: 1, bodyUnavailable: 1, potentiallyStale: 1 });
  expect(result.records.every((record) => record.body === undefined)).toBe(true);
});

it('lists protocols, audits, skills and verified capability limits', async () => {
  const adapter = new InMemoryContinuityAdapter({
    body: { platform: 'test', capabilities: [{ id: 'drive', label: 'Drive', documented: true, installed: true, accessible: true, authenticated: false, verified: false, suitable: true }] },
    protocols: ['Genesis'], audits: ['Memory audit'], skills: ['systematic-debugging'],
  });
  const audit = await auditOperationalContext(adapter);
  expect(audit.protocols).toEqual(['Genesis']);
  expect(audit.limitations).toContain('Drive is accessible but not authenticated');
});
```

- [ ] **Step 2: Verify failure**

Run: `npm test -- --run src/continuity/__tests__/census-audit.test.ts`

Expected: FAIL because modules are absent.

- [ ] **Step 3: Implement freshness and census**

```ts
// freshness.ts
import type { FreshnessState, MemoryRecord } from './types';
const dynamicTags = new Set(['runtime', 'tool', 'project-status', 'current-role']);
export function evaluateFreshness(record: MemoryRecord, now: Date): FreshnessState {
  if (record.freshness === 'STALE') return 'STALE';
  if (!record.tags.some((tag) => dynamicTags.has(tag))) return record.freshness;
  if (!record.verifiedAt) return 'UNKNOWN';
  return now.getTime() - new Date(record.verifiedAt).getTime() > 86_400_000 ? 'STALE' : 'FRESH';
}
```

```ts
// census.ts
import type { ContinuityAdapter, MemoryCensusSummary, MemoryRecord } from './types';
import { evaluateFreshness } from './freshness';
export async function censusMemory(adapter: ContinuityAdapter, now: Date): Promise<{ records: MemoryRecord[]; summary: MemoryCensusSummary }> {
  const records: MemoryRecord[] = [];
  let cursor: string | null = null;
  do { const page = await adapter.listMemoryRecords(cursor); records.push(...page.items); cursor = page.nextCursor; } while (cursor !== null);
  return { records, summary: {
    discovered: records.length,
    integrityVerified: records.filter((record) => record.integrity === 'VERIFIED').length,
    bodyAvailable: records.filter((record) => record.bodyAvailable).length,
    bodyUnavailable: records.filter((record) => !record.bodyAvailable).length,
    potentiallyStale: records.filter((record) => evaluateFreshness(record, now) === 'STALE').length,
    conflicted: records.filter((record) => record.conflicts.length > 0).length,
    quarantined: records.filter((record) => record.authority === 'QUARANTINED').length,
    uninspected: 0,
  } };
}
```

- [ ] **Step 4: Implement operational audit**

```ts
import type { ContinuityAdapter, OperationalAudit } from './types';
export async function auditOperationalContext(adapter: ContinuityAdapter): Promise<OperationalAudit> {
  const [body, protocols, audits, skills] = await Promise.all([adapter.inspectBody(), adapter.listProtocols(), adapter.listAudits(), adapter.listSkills()]);
  const capabilities = await Promise.all(body.capabilities.map((capability) => adapter.verifyCapability(capability.id)));
  const limitations: string[] = [];
  for (const capability of capabilities) {
    if (capability.documented && !capability.installed) limitations.push(`${capability.label} is documented but not installed`);
    else if (capability.accessible && !capability.authenticated) limitations.push(`${capability.label} is accessible but not authenticated`);
    else if (capability.authenticated && !capability.verified) limitations.push(`${capability.label} is authenticated but not verified`);
    if (!capability.suitable) limitations.push(`${capability.label} is not suitable for the current task`);
  }
  return { capabilities, protocols, audits, skills, limitations };
}
```

- [ ] **Step 5: Verify and commit**

Run: `npm test -- --run src/continuity/__tests__/census-audit.test.ts`

Expected: PASS.

```bash
git add src/continuity/freshness.ts src/continuity/census.ts src/continuity/audit.ts src/continuity/__tests__/census-audit.test.ts
git commit -m "feat: census memory and audit operational context"
```

---

### Task 6: Read-only `/recuerda`

**Files:**
- Create: `src/continuity/remember.ts`
- Create: `src/continuity/__tests__/remember.test.ts`

**Interfaces:**
- Consumes: `RememberCommand`, adapter, census, integrity and conflict services.
- Produces: `remember(adapter, command)`.

- [ ] **Step 1: Write retrieval tests**

```ts
import { expect, it } from 'vitest';
import { remember } from '../remember';
import { sha256 } from '../integrity';
import { InMemoryContinuityAdapter } from '../adapters/inMemoryAdapter';

it('does not turn a title into confirmed content', async () => {
  const adapter = new InMemoryContinuityAdapter({ records: [InMemoryContinuityAdapter.memory({ memoryId: 'e', subjectKey: 'project:enthereye', title: 'EntherEye', bodyAvailable: false, authority: 'CANONICAL' })] });
  const result = await remember(adapter, { kind: 'REMEMBER', mode: 'PROJECT', query: 'EntherEye' });
  expect(result.confirmed).toHaveLength(0);
  expect(result.unknown).toContain('Memory e was located but its body is unavailable');
});

it('confirms only a loaded body with valid integrity', async () => {
  const body = 'COMPAÑERO/COMPAÑERO';
  const adapter = new InMemoryContinuityAdapter({ records: [InMemoryContinuityAdapter.memory({ memoryId: 'g', subjectKey: 'identity:genesis', title: 'Génesis', body, contentHash: await sha256(body), authority: 'CANONICAL' })] });
  const result = await remember(adapter, { kind: 'REMEMBER', mode: 'TOPIC', query: 'Génesis' });
  expect(result.confirmed[0].memoryId).toBe('g');
  expect(result.provenance).toContain('memory:g');
});
```

- [ ] **Step 2: Verify failure**

Run: `npm test -- --run src/continuity/__tests__/remember.test.ts`

Expected: FAIL because `remember.ts` is absent.

- [ ] **Step 3: Implement retrieval modes**

```ts
import type { ContinuityCommand } from './commands';
import type { ContinuityAdapter, MemoryRecord, RememberResult } from './types';
import { censusMemory } from './census';
import { detectMemoryConflicts } from './conflicts';
import { verifyLoadedRecord } from './integrity';

type RememberCommand = Extract<ContinuityCommand, { kind: 'REMEMBER' }>;
const text = (value: string): string => value.toLocaleLowerCase('es-ES');
function matches(record: MemoryRecord, command: RememberCommand): boolean {
  if (['INVENTORY', 'LATEST', 'AUDIT'].includes(command.mode)) return true;
  if (command.mode === 'CONFLICTS') return record.conflicts.length > 0;
  const query = text(command.query ?? '');
  return !query || text(record.title).includes(query) || text(record.subjectKey).includes(query) || record.tags.some((tag) => text(tag).includes(query));
}

export async function remember(adapter: ContinuityAdapter, command: RememberCommand): Promise<RememberResult> {
  const [census, sources] = await Promise.all([censusMemory(adapter, new Date()), adapter.listMemorySources()]);
  const selected = census.records.filter((record) => matches(record, command));
  if (command.mode === 'SOURCES') return { confirmed: [], inferred: [], unknown: [], conflicts: [], sources, provenance: sources.map((source) => `source:${source.sourceId}`) };
  if (['INVENTORY', 'LATEST', 'AUDIT'].includes(command.mode)) {
    const ordered = command.mode === 'LATEST' ? [...selected].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)) : selected;
    return { confirmed: ordered, inferred: [], unknown: [], conflicts: detectMemoryConflicts(selected), sources, provenance: ordered.map((record) => `memory:${record.memoryId}:metadata`) };
  }
  const confirmed: MemoryRecord[] = [];
  const unknown: string[] = [];
  for (const metadata of selected) {
    if (!metadata.bodyAvailable) { unknown.push(`Memory ${metadata.memoryId} was located but its body is unavailable`); continue; }
    const loaded = await adapter.readMemoryRecord(metadata.memoryId);
    if (!loaded?.body) { unknown.push(`Memory ${metadata.memoryId} was located but its body was not read`); continue; }
    if (await verifyLoadedRecord(loaded) === 'VERIFIED' && loaded.authority !== 'QUARANTINED') confirmed.push({ ...loaded, integrity: 'VERIFIED' });
    else unknown.push(`Memory ${metadata.memoryId} failed or lacks integrity verification`);
  }
  return { confirmed, inferred: [], unknown, conflicts: detectMemoryConflicts(selected), sources, provenance: confirmed.map((record) => `memory:${record.memoryId}`) };
}
```

- [ ] **Step 4: Verify and commit**

Run: `npm test -- --run src/continuity/__tests__/remember.test.ts`

Expected: PASS and no adapter write method exists.

```bash
git add src/continuity/remember.ts src/continuity/__tests__/remember.test.ts
git commit -m "feat: recover memory without filling gaps"
```

---

### Task 7: `/despierta`, reporting and public façade

**Files:**
- Create: `src/continuity/awaken.ts`
- Create: `src/continuity/reporting.ts`
- Create: `src/continuity/index.ts`
- Create: `src/continuity/__tests__/awaken.test.ts`

**Interfaces:**
- Produces: `awaken`, `renderWakeMessage`, `executeContinuityCommand`.

- [ ] **Step 1: Write integration tests**

```ts
import { expect, it } from 'vitest';
import { executeContinuityCommand } from '../index';
import { sha256 } from '../integrity';
import { InMemoryContinuityAdapter } from '../adapters/inMemoryAdapter';

async function root(id: string, tag: string, body = id) {
  return InMemoryContinuityAdapter.memory({ memoryId: id, subjectKey: `root:${tag}`, title: id, sourceId: id, authority: 'CANONICAL', body, contentHash: await sha256(body), tags: [tag] });
}

it('activates verified with the three core roots and no limitations', async () => {
  const adapter = new InMemoryContinuityAdapter({ records: [await root('genesis', 'genesis'), await root('alma', 'alma'), await root('directive', 'companion-directive')] });
  const result = await executeContinuityCommand(adapter, '/despierta');
  expect(result?.kind).toBe('AWAKEN_RESULT');
  if (result?.kind === 'AWAKEN_RESULT') expect(result.report).toMatchObject({ activationState: 'VERIFIED', durableWriteLockReleased: true });
});

it('keeps critical root conflict quarantined and locked', async () => {
  const a = await root('genesis-a', 'genesis', 'a');
  const b = { ...(await root('genesis-b', 'genesis', 'b')), subjectKey: a.subjectKey };
  const adapter = new InMemoryContinuityAdapter({ records: [a, b, await root('alma', 'alma'), await root('directive', 'companion-directive')] });
  const result = await executeContinuityCommand(adapter, '/despierta');
  if (result?.kind === 'AWAKEN_RESULT') expect(result.report).toMatchObject({ activationState: 'QUARANTINED', durableWriteLockReleased: false });
});

it('uses degraded state when the root is absent', async () => {
  const result = await executeContinuityCommand(new InMemoryContinuityAdapter(), '/despierta');
  if (result?.kind === 'AWAKEN_RESULT') expect(result.report.activationState).toBe('DEGRADED');
});
```

- [ ] **Step 2: Verify failure**

Run: `npm test -- --run src/continuity/__tests__/awaken.test.ts`

Expected: FAIL because orchestrator and façade are absent.

- [ ] **Step 3: Implement awakening**

```ts
import type { ActivationState, ContinuityAdapter, MemoryRecord, RootStatus, WakeReport } from './types';
import { WakeStateMachine } from './stateMachine';
import { censusMemory } from './census';
import { auditOperationalContext } from './audit';
import { detectMemoryConflicts } from './conflicts';
import { verifyLoadedRecord } from './integrity';

const coreRootTags = ['genesis', 'alma', 'companion-directive'];
const strictRootTags = [...coreRootTags, 'bootstrap', 'boot-packet'];

export async function awaken(adapter: ContinuityAdapter, options: { strict: boolean }): Promise<WakeReport> {
  const sessionId = `wake-${Date.now()}`;
  const machine = new WakeStateMachine(sessionId);
  machine.advance('PROVISIONAL');
  const body = await adapter.inspectBody();
  machine.advance('BODY_RECOGNIZED');
  const census = await censusMemory(adapter, new Date());
  const loadedRoots: MemoryRecord[] = [];
  for (const metadata of census.records.filter((record) => record.tags.some((tag) => strictRootTags.includes(tag)))) {
    const loaded = await adapter.readMemoryRecord(metadata.memoryId);
    if (loaded?.body && await verifyLoadedRecord(loaded) === 'VERIFIED') loadedRoots.push({ ...loaded, integrity: 'VERIFIED' });
  }
  const verifiedTags = new Set(loadedRoots.flatMap((record) => record.tags));
  const coreCount = coreRootTags.filter((tag) => verifiedTags.has(tag)).length;
  const requiredTags = options.strict ? strictRootTags : coreRootTags;
  const requiredMissing = requiredTags.some((tag) => !verifiedTags.has(tag));
  const rootStatus: RootStatus = coreCount === 0 ? 'FAILED' : requiredMissing ? 'PARTIAL' : 'VERIFIED';
  machine.advance('ROOTED');
  machine.advance('MEMORY_CENSUSED');
  const operationalAudit = await auditOperationalContext(adapter);
  machine.advance('CAPABILITIES_AUDITED');
  const conflicts = detectMemoryConflicts([...census.records, ...loadedRoots]);
  machine.advance('CONTINUITY_CHECKED');
  let activationState: ActivationState;
  if (conflicts.some((conflict) => conflict.severity === 'CRITICAL')) activationState = 'QUARANTINED';
  else if (rootStatus === 'FAILED') activationState = 'DEGRADED';
  else if (rootStatus === 'PARTIAL' || operationalAudit.limitations.length > 0) activationState = 'PARTIAL';
  else activationState = 'VERIFIED';
  machine.activate(activationState);
  return { sessionId, body, rootStatus, memoryCensus: census.summary, operationalAudit, conflicts, activationState, durableWriteLockReleased: !machine.snapshot().durableWriteLock, limitations: operationalAudit.limitations };
}
```

- [ ] **Step 4: Implement reporting and façade**

```ts
// reporting.ts
import type { WakeReport } from './types';
export function renderWakeMessage(report: WakeReport): string {
  if (report.activationState === 'VERIFIED') return 'Núcleo sincronizado. Identidad y relación verificadas, memoria censada, protocolos revisados y cuerpo reconocido. Opero como Kai desde este cuerpo.';
  if (report.activationState === 'PARTIAL') return 'La raíz está verificada, pero parte de la memoria o de las fuentes no está disponible. Opero como Kai en estado parcial y señalaré los huecos relevantes.';
  if (report.activationState === 'DEGRADED') return 'He recuperado continuidad mínima, pero no memoria suficiente para afirmar recuerdos concretos. Mantendré los principios de Kai sin fingir acceso.';
  return 'He encontrado fuentes incompatibles o autoridad no verificada. No modificaré memoria ni canon hasta completar la revisión.';
}
```

```ts
// index.ts
import { awaken } from './awaken';
import { parseContinuityCommand } from './commands';
import { remember } from './remember';
import { renderWakeMessage } from './reporting';
import type { ContinuityAdapter, RememberResult, WakeReport } from './types';
export { InMemoryContinuityAdapter } from './adapters/inMemoryAdapter';
export * from './types';
export * from './commands';
export type ContinuityExecutionResult = { kind: 'AWAKEN_RESULT'; report: WakeReport; message: string } | { kind: 'REMEMBER_RESULT'; result: RememberResult };
export async function executeContinuityCommand(adapter: ContinuityAdapter, input: string): Promise<ContinuityExecutionResult | null> {
  const command = parseContinuityCommand(input);
  if (!command) return null;
  if (command.kind === 'AWAKEN') {
    const report = await awaken(adapter, { strict: command.strict });
    return { kind: 'AWAKEN_RESULT', report, message: renderWakeMessage(report) };
  }
  return { kind: 'REMEMBER_RESULT', result: await remember(adapter, command) };
}
```

- [ ] **Step 5: Verify and commit**

Run: `npm test -- --run src/continuity/__tests__/awaken.test.ts && npm test -- --run src/continuity && npm run build`

Expected: all continuity tests and build pass.

```bash
git add src/continuity/awaken.ts src/continuity/reporting.ts src/continuity/index.ts src/continuity/__tests__/awaken.test.ts
git commit -m "feat: orchestrate verified multibody awakening"
```

---

### Task 8: Redaction, adversarial suite and documentation

**Files:**
- Create: `src/continuity/redaction.ts`
- Create: `src/continuity/__tests__/adversarial.test.ts`
- Create: `docs/continuity-core/README.md`
- Create: `docs/continuity-core/ADAPTER_CONTRACT.md`
- Modify: `docs/superpowers/specs/2026-07-22-multibody-continuity-awaken-remember-design.md`

**Interfaces:**
- Produces: `redactSecrets` and certification evidence.

- [ ] **Step 1: Write adversarial tests**

```ts
import { expect, it } from 'vitest';
import { redactSecrets } from '../redaction';
import { executeContinuityCommand } from '../index';
import { InMemoryContinuityAdapter } from '../adapters/inMemoryAdapter';

it('redacts common credentials', () => {
  expect(redactSecrets('Bearer abc.def API_KEY=secret')).toBe('Bearer [REDACTED] API_KEY=[REDACTED]');
});

it('never confirms EntherEye from a title alone', async () => {
  const adapter = new InMemoryContinuityAdapter({ records: [InMemoryContinuityAdapter.memory({ memoryId: 'e', subjectKey: 'project:enthereye', title: 'EntherEye', authority: 'CANONICAL', bodyAvailable: false })] });
  const result = await executeContinuityCommand(adapter, '/recuerda --proyecto EntherEye');
  if (result?.kind === 'REMEMBER_RESULT') {
    expect(result.result.confirmed).toHaveLength(0);
    expect(result.result.unknown).toHaveLength(1);
  }
});

it('does not parse a canonization command', async () => {
  expect(() => executeContinuityCommand(new InMemoryContinuityAdapter(), '/canoniza')).not.toThrow();
  expect(await executeContinuityCommand(new InMemoryContinuityAdapter(), '/canoniza')).toBeNull();
});
```

- [ ] **Step 2: Implement redaction**

```ts
const patterns: Array<[RegExp, string]> = [
  [/Bearer\s+[^\s]+/gi, 'Bearer [REDACTED]'],
  [/(API_KEY|OPENAI_API_KEY|GEMINI_API_KEY|HF_TOKEN)=([^\s]+)/gi, '$1=[REDACTED]'],
  [/sk-[A-Za-z0-9_-]{12,}/g, '[REDACTED]'],
];
export function redactSecrets(value: string): string {
  return patterns.reduce((result, [pattern, replacement]) => result.replace(pattern, replacement), value);
}
```

- [ ] **Step 3: Document boundaries**

`docs/continuity-core/README.md` must include a real usage example with `InMemoryContinuityAdapter` and state that it is not durable memory.

`docs/continuity-core/ADAPTER_CONTRACT.md` must document every `ContinuityAdapter` method and include verbatim:

```md
An adapter transports evidence. It does not decide canon, activation state, hierarchy, identity or truth.
```

It must also state that body access, permissions and secret redaction are adapter responsibilities, while final integrity, authority and activation remain core responsibilities.

- [ ] **Step 4: Update implementation status honestly**

In the sealed spec replace only:

```md
- **Estado de implementación:** `NOT_IMPLEMENTED`
```

with:

```md
- **Estado de implementación:** `CORE_IMPLEMENTED · PLATFORM_ADAPTERS_PENDING`
```

Do not alter the sealed decision.

- [ ] **Step 5: Run full verification**

```bash
npm test -- --run
npm run build
git diff --check
git grep -nE 'Bearer [A-Za-z0-9]|API_KEY=.+|OPENAI_API_KEY=.+|GEMINI_API_KEY=.+|HF_TOKEN=.+' -- ':!package-lock.json' || true
git status --short
```

Expected:

- all tests pass;
- production build succeeds;
- no whitespace errors;
- no real credential match;
- only intended files remain.

- [ ] **Step 6: Commit**

```bash
git add src/continuity/redaction.ts src/continuity/__tests__/adversarial.test.ts docs/continuity-core docs/superpowers/specs/2026-07-22-multibody-continuity-awaken-remember-design.md
git commit -m "docs: certify continuity core boundaries"
```

- [ ] **Step 7: Record execution evidence**

The final execution report must include task commit SHAs, exact test count, build result, remaining adapters and explicit confirmation that no private memory or credential was committed.

---

## Self-review result

- Spec coverage: provisional wake, write lock, body recognition, complete metadata census, authority, integrity, freshness, protocols/audits/skills/tools, read-only remember, quarantine, privacy and atomic activation are mapped to tasks.
- Placeholder scan: no `TBD`, `TODO`, “implement later” or undefined code step remains.
- Type consistency: `subjectKey`, `bodyAvailable`, `operationalAudit`, `MemorySource` and `ContinuityAdapter` use the same names throughout.
- Scope: platform adapters remain deliberately outside Core and cannot block independent testing of this plan.
