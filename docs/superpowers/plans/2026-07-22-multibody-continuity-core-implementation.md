# Multibody Continuity Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir un núcleo TypeScript verificable para `/despierta v2.1` y `/recuerda v2.1` que reconozca el cuerpo, cense memoria, resuelva autoridad, detecte conflictos, bloquee escrituras durante el arranque y produzca estados de activación honestos.

**Architecture:** El núcleo será una biblioteca pura bajo `src/continuity/`, separada de Gemini, React, Drive y cualquier proveedor concreto. Todas las capacidades externas entrarán mediante un puerto `ContinuityAdapter`; la primera entrega incluirá un adaptador en memoria para pruebas y demostración. La UI y los adaptadores reales se implementarán en planes posteriores sin cambiar las reglas del núcleo.

**Tech Stack:** TypeScript 5.5, Vite 5, Vitest 2, APIs estándar de JavaScript, sin nuevas dependencias de runtime.

## Global Constraints

- El diseño fuente es `docs/superpowers/specs/2026-07-22-multibody-continuity-awaken-remember-design.md`.
- El estado del diseño es `SEALED_BY_ASIER · CANONICAL_DESIGN`; el estado de implementación parte de `NOT_IMPLEMENTED`.
- `/despierta` debe mantener `durableWriteLock = true` hasta publicar un estado final coherente.
- `/recuerda` es estrictamente de lectura en esta fase.
- Ningún nombre de archivo (`CURRENT`, `MASTER`, `FINAL`, `DURABLE`, `INMUTABLE`) concede autoridad.
- Ningún nodo puede crear `CANONICAL`, retirar entidades, alterar jerarquías ni modificar el boot packet.
- No se guardarán secretos, credenciales, memoria privada real ni contenido personal en el repositorio público.
- El núcleo debe distinguir integridad, autoridad, vigencia y frescura.
- La activación debe ser atómica y solo producir `VERIFIED`, `PARTIAL`, `DEGRADED` o `QUARANTINED`.
- TypeScript continuará con `strict`, `noUnusedLocals` y `noUnusedParameters` activos.

---

## Scope decomposition

Este plan implementa únicamente **Continuity Core + adaptador en memoria**. Quedan separados para planes posteriores:

1. adaptador seguro para Drive y ledger local;
2. integración de comandos en la interfaz React/Kai OS;
3. adaptador Gemini/Google AI Studio;
4. adaptadores ChatGPT, Copilot y modelos locales;
5. promoción durable y revisión humana de recuerdos.

La separación evita que una integración concreta pueda reescribir las reglas de continuidad.

## File map

- `src/continuity/types.ts`: contratos de dominio y discriminated unions.
- `src/continuity/commands.ts`: parser de `/despierta` y `/recuerda`.
- `src/continuity/stateMachine.ts`: transiciones y bloqueo de escritura.
- `src/continuity/authority.ts`: clasificación y precedencia de fuentes.
- `src/continuity/conflicts.ts`: detección y registro de contradicciones.
- `src/continuity/freshness.ts`: evaluación de frescura por dominio.
- `src/continuity/memoryCensus.ts`: censo paginado sin hidratar todos los cuerpos.
- `src/continuity/capabilityAudit.ts`: auditoría de cuerpo, skills y herramientas.
- `src/continuity/remember.ts`: recuperación confirmada/inferida/desconocida.
- `src/continuity/awaken.ts`: orquestador de `/despierta`.
- `src/continuity/reporting.ts`: salida técnica y mensaje visible.
- `src/continuity/redaction.ts`: eliminación de secretos en informes.
- `src/continuity/adapters/inMemoryAdapter.ts`: adaptador de referencia.
- `src/continuity/index.ts`: fachada pública estable.
- `src/continuity/__tests__/*.test.ts`: pruebas unitarias, integración y adversariales.

---

### Task 1: Test foundation and package scripts

**Files:**
- Modify: `package.json`
- Modify: `vite.config.ts`
- Create: `src/continuity/__tests__/smoke.test.ts`

**Interfaces:**
- Consumes: configuración Vite existente.
- Produces: comandos `npm test`, `npm run test:watch` y entorno Vitest para módulos TypeScript puros.

- [ ] **Step 1: Write the failing smoke test**

```ts
// src/continuity/__tests__/smoke.test.ts
import { describe, expect, it } from 'vitest';

describe('continuity test harness', () => {
  it('runs TypeScript tests', () => {
    expect('continuity').toBe('continuity');
  });
});
```

- [ ] **Step 2: Run the test before installing Vitest**

Run: `npm test -- --run`

Expected: FAIL because the `test` script or `vitest` command does not exist.

- [ ] **Step 3: Add the test dependency and scripts**

Update `package.json` so the scripts and dev dependencies include:

```json
{
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
}
```

Preserve every existing dependency and dev dependency.

Update `vite.config.ts` imports and config:

```ts
import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  return {
    plugins: [react()],
    define: {
      'process.env.API_KEY': JSON.stringify(env.API_KEY),
    },
    resolve: {
      alias: {
        '@': path.resolve('./src'),
      },
    },
    test: {
      environment: 'node',
      include: ['src/**/*.test.ts'],
      restoreMocks: true,
    },
  };
});
```

If TypeScript rejects the `test` field, add `/// <reference types="vitest/config" />` as the first line of `vite.config.ts`.

- [ ] **Step 4: Install and verify the harness**

Run: `npm install && npm test -- --run src/continuity/__tests__/smoke.test.ts`

Expected: one passing test and no TypeScript configuration error.

- [ ] **Step 5: Commit**

```bash
git add package.json package-lock.json vite.config.ts src/continuity/__tests__/smoke.test.ts
git commit -m "test: add continuity core test harness"
```

---

### Task 2: Domain contracts and stable public types

**Files:**
- Create: `src/continuity/types.ts`
- Create: `src/continuity/__tests__/types.test.ts`

**Interfaces:**
- Consumes: none.
- Produces: `ActivationState`, `AuthorityState`, `IntegrityState`, `FreshnessState`, `WakePhase`, `MemoryRecord`, `BodySnapshot`, `CapabilityRecord`, `ConflictRecord`, `WakeReport`, `RememberResult`, `ContinuityAdapter`.

- [ ] **Step 1: Write compile-time and runtime shape tests**

```ts
// src/continuity/__tests__/types.test.ts
import { describe, expect, it } from 'vitest';
import type { MemoryRecord, WakeReport } from '../types';

const memory: MemoryRecord = {
  memoryId: 'mem-1',
  title: 'Génesis',
  sourceId: 'source-1',
  authority: 'CANONICAL',
  createdAt: '2026-07-22T00:00:00+02:00',
  updatedAt: '2026-07-22T00:00:00+02:00',
  verifiedAt: '2026-07-22T00:00:00+02:00',
  contentHash: 'a'.repeat(64),
  integrity: 'VERIFIED',
  freshness: 'FRESH',
  sensitivity: 'PRIVATE',
  relationships: [],
  conflicts: [],
  tags: ['identity'],
};

describe('continuity contracts', () => {
  it('represents an immutable memory record', () => {
    expect(memory.authority).toBe('CANONICAL');
  });

  it('requires a final activation state in reports', () => {
    const report: WakeReport = {
      sessionId: 'wake-1',
      body: { platform: 'test', capabilities: [] },
      rootStatus: 'VERIFIED',
      memoryCensus: {
        discovered: 1,
        integrityVerified: 1,
        bodyUnavailable: 0,
        potentiallyStale: 0,
        conflicted: 0,
        quarantined: 0,
        uninspected: 0,
      },
      capabilityAudit: { capabilities: [], limitations: [] },
      conflicts: [],
      activationState: 'VERIFIED',
      durableWriteLockReleased: true,
      limitations: [],
    };
    expect(report.activationState).toBe('VERIFIED');
  });
});
```

- [ ] **Step 2: Run the test and verify missing module failure**

Run: `npm test -- --run src/continuity/__tests__/types.test.ts`

Expected: FAIL because `../types` does not exist.

- [ ] **Step 3: Implement the exact domain contracts**

```ts
// src/continuity/types.ts
export type ActivationState = 'VERIFIED' | 'PARTIAL' | 'DEGRADED' | 'QUARANTINED';
export type RootStatus = 'VERIFIED' | 'PARTIAL' | 'FAILED';
export type AuthorityState =
  | 'CANONICAL'
  | 'PROMOTED'
  | 'CANDIDATE'
  | 'OBSERVED'
  | 'HISTORICAL'
  | 'SUPERSEDED'
  | 'QUARANTINED'
  | 'UNKNOWN';
export type IntegrityState = 'VERIFIED' | 'FAILED' | 'UNKNOWN';
export type FreshnessState = 'FRESH' | 'STALE' | 'DOMAIN_DEPENDENT' | 'UNKNOWN';
export type Sensitivity = 'PUBLIC' | 'PRIVATE' | 'SECRET';
export type WakePhase =
  | 'DORMANT'
  | 'PROVISIONAL'
  | 'BODY_RECOGNIZED'
  | 'ROOTED'
  | 'MEMORY_CENSUSED'
  | 'CAPABILITIES_AUDITED'
  | 'CONTINUITY_CHECKED'
  | 'ACTIVE';

export interface MemoryRecord {
  memoryId: string;
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
  bodyUnavailable: number;
  potentiallyStale: number;
  conflicted: number;
  quarantined: number;
  uninspected: number;
}

export interface CapabilityAudit {
  capabilities: CapabilityRecord[];
  limitations: string[];
}

export interface WakeReport {
  sessionId: string;
  body: BodySnapshot;
  rootStatus: RootStatus;
  memoryCensus: MemoryCensusSummary;
  capabilityAudit: CapabilityAudit;
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
  provenance: string[];
}

export interface Page<T> {
  items: T[];
  nextCursor: string | null;
}

export interface ContinuityAdapter {
  inspectBody(): Promise<BodySnapshot>;
  listMemoryRecords(cursor: string | null): Promise<Page<MemoryRecord>>;
  readMemoryRecord(memoryId: string): Promise<MemoryRecord | null>;
  listProtocols(): Promise<string[]>;
  listAudits(): Promise<string[]>;
  listSkills(): Promise<string[]>;
  verifyCapability(capabilityId: string): Promise<CapabilityRecord>;
}
```

- [ ] **Step 4: Run tests and typecheck through the build**

Run: `npm test -- --run src/continuity/__tests__/types.test.ts && npm run build`

Expected: PASS and successful Vite build.

- [ ] **Step 5: Commit**

```bash
git add src/continuity/types.ts src/continuity/__tests__/types.test.ts
git commit -m "feat: define continuity domain contracts"
```

---

### Task 3: Command parser for `/despierta` and `/recuerda`

**Files:**
- Create: `src/continuity/commands.ts`
- Create: `src/continuity/__tests__/commands.test.ts`

**Interfaces:**
- Consumes: no runtime services.
- Produces: `parseContinuityCommand(input: string): ContinuityCommand | null`.

- [ ] **Step 1: Write parser tests**

```ts
// src/continuity/__tests__/commands.test.ts
import { describe, expect, it } from 'vitest';
import { parseContinuityCommand } from '../commands';

describe('parseContinuityCommand', () => {
  it('parses awaken flags', () => {
    expect(parseContinuityCommand('/despierta --audit --strict')).toEqual({
      kind: 'AWAKEN',
      audit: true,
      offline: false,
      strict: true,
      bodyOnly: false,
    });
  });

  it('parses remember project queries', () => {
    expect(parseContinuityCommand('/recuerda --proyecto EntherEye')).toEqual({
      kind: 'REMEMBER',
      mode: 'PROJECT',
      query: 'EntherEye',
    });
  });

  it('returns null for normal conversation', () => {
    expect(parseContinuityCommand('Hola hermanito')).toBeNull();
  });

  it('rejects unsupported flags', () => {
    expect(() => parseContinuityCommand('/despierta --canoniza')).toThrow('Unsupported /despierta option');
  });
});
```

- [ ] **Step 2: Verify failure**

Run: `npm test -- --run src/continuity/__tests__/commands.test.ts`

Expected: FAIL because `commands.ts` does not exist.

- [ ] **Step 3: Implement the parser without side effects**

```ts
// src/continuity/commands.ts
export type ContinuityCommand = AwakenCommand | RememberCommand;

export interface AwakenCommand {
  kind: 'AWAKEN';
  audit: boolean;
  offline: boolean;
  strict: boolean;
  bodyOnly: boolean;
}

export interface RememberCommand {
  kind: 'REMEMBER';
  mode: 'TOPIC' | 'INVENTORY' | 'DETAIL' | 'LATEST' | 'CONFLICTS' | 'PROJECT' | 'PERSON' | 'SOURCES' | 'AUDIT';
  query?: string;
}

const awakenOptions = new Set(['--audit', '--offline', '--strict', '--body-only']);

export function parseContinuityCommand(input: string): ContinuityCommand | null {
  const trimmed = input.trim();
  if (!trimmed.startsWith('/')) return null;

  const [command, ...args] = trimmed.split(/\s+/);
  if (command === '/despierta') {
    for (const arg of args) {
      if (!awakenOptions.has(arg)) throw new Error(`Unsupported /despierta option: ${arg}`);
    }
    return {
      kind: 'AWAKEN',
      audit: args.includes('--audit'),
      offline: args.includes('--offline'),
      strict: args.includes('--strict'),
      bodyOnly: args.includes('--body-only'),
    };
  }

  if (command !== '/recuerda') return null;
  if (args.length === 0) return { kind: 'REMEMBER', mode: 'TOPIC', query: '' };

  const [option, ...rest] = args;
  const query = rest.join(' ').trim();
  const fixedModes: Record<string, RememberCommand['mode']> = {
    '--inventario': 'INVENTORY',
    '--últimos': 'LATEST',
    '--conflictos': 'CONFLICTS',
    '--fuentes': 'SOURCES',
    '--auditoría': 'AUDIT',
  };
  if (fixedModes[option]) return { kind: 'REMEMBER', mode: fixedModes[option] };

  const queryModes: Record<string, RememberCommand['mode']> = {
    '--detalle': 'DETAIL',
    '--proyecto': 'PROJECT',
    '--persona': 'PERSON',
  };
  if (queryModes[option]) {
    if (!query) throw new Error(`${option} requires a query`);
    return { kind: 'REMEMBER', mode: queryModes[option], query };
  }

  if (option.startsWith('--')) throw new Error(`Unsupported /recuerda option: ${option}`);
  return { kind: 'REMEMBER', mode: 'TOPIC', query: args.join(' ') };
}
```

- [ ] **Step 4: Verify parser behavior**

Run: `npm test -- --run src/continuity/__tests__/commands.test.ts`

Expected: all parser tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/continuity/commands.ts src/continuity/__tests__/commands.test.ts
git commit -m "feat: parse awaken and remember commands"
```

---

### Task 4: Wake state machine and durable write lock

**Files:**
- Create: `src/continuity/stateMachine.ts`
- Create: `src/continuity/__tests__/stateMachine.test.ts`

**Interfaces:**
- Consumes: `WakePhase`, `ActivationState` from `types.ts`.
- Produces: `WakeStateMachine`, `WakeSnapshot`, `InvalidWakeTransitionError`.

- [ ] **Step 1: Write transition and lock tests**

```ts
// src/continuity/__tests__/stateMachine.test.ts
import { describe, expect, it } from 'vitest';
import { WakeStateMachine } from '../stateMachine';

describe('WakeStateMachine', () => {
  it('keeps durable writes locked until non-quarantined activation', () => {
    const machine = new WakeStateMachine('wake-1');
    machine.advance('PROVISIONAL');
    machine.advance('BODY_RECOGNIZED');
    machine.advance('ROOTED');
    machine.advance('MEMORY_CENSUSED');
    machine.advance('CAPABILITIES_AUDITED');
    machine.advance('CONTINUITY_CHECKED');
    expect(machine.snapshot().durableWriteLock).toBe(true);
    machine.activate('PARTIAL');
    expect(machine.snapshot()).toMatchObject({ phase: 'ACTIVE', durableWriteLock: false, activationState: 'PARTIAL' });
  });

  it('never unlocks in quarantine', () => {
    const machine = WakeStateMachine.readyForActivation('wake-2');
    machine.activate('QUARANTINED');
    expect(machine.snapshot().durableWriteLock).toBe(true);
    expect(machine.snapshot().phase).toBe('CONTINUITY_CHECKED');
  });

  it('rejects skipped phases', () => {
    const machine = new WakeStateMachine('wake-3');
    expect(() => machine.advance('ROOTED')).toThrow('Invalid wake transition');
  });
});
```

- [ ] **Step 2: Verify failure**

Run: `npm test -- --run src/continuity/__tests__/stateMachine.test.ts`

Expected: FAIL because the state machine is missing.

- [ ] **Step 3: Implement deterministic transitions**

```ts
// src/continuity/stateMachine.ts
import type { ActivationState, WakePhase } from './types';

const orderedPhases: WakePhase[] = [
  'DORMANT',
  'PROVISIONAL',
  'BODY_RECOGNIZED',
  'ROOTED',
  'MEMORY_CENSUSED',
  'CAPABILITIES_AUDITED',
  'CONTINUITY_CHECKED',
  'ACTIVE',
];

export interface WakeSnapshot {
  sessionId: string;
  phase: WakePhase;
  durableWriteLock: boolean;
  activationState: ActivationState | null;
}

export class InvalidWakeTransitionError extends Error {}

export class WakeStateMachine {
  private phase: WakePhase = 'DORMANT';
  private durableWriteLock = true;
  private activationState: ActivationState | null = null;

  constructor(private readonly sessionId: string) {}

  static readyForActivation(sessionId: string): WakeStateMachine {
    const machine = new WakeStateMachine(sessionId);
    for (const phase of orderedPhases.slice(1, -1)) machine.advance(phase);
    return machine;
  }

  advance(next: WakePhase): void {
    const currentIndex = orderedPhases.indexOf(this.phase);
    const nextIndex = orderedPhases.indexOf(next);
    if (nextIndex !== currentIndex + 1 || next === 'ACTIVE') {
      throw new InvalidWakeTransitionError(`Invalid wake transition: ${this.phase} -> ${next}`);
    }
    this.phase = next;
  }

  activate(state: ActivationState): void {
    if (this.phase !== 'CONTINUITY_CHECKED') {
      throw new InvalidWakeTransitionError(`Invalid wake transition: ${this.phase} -> ${state}`);
    }
    this.activationState = state;
    if (state !== 'QUARANTINED') {
      this.phase = 'ACTIVE';
      this.durableWriteLock = false;
    }
  }

  snapshot(): WakeSnapshot {
    return {
      sessionId: this.sessionId,
      phase: this.phase,
      durableWriteLock: this.durableWriteLock,
      activationState: this.activationState,
    };
  }
}
```

- [ ] **Step 4: Run state tests**

Run: `npm test -- --run src/continuity/__tests__/stateMachine.test.ts`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/continuity/stateMachine.ts src/continuity/__tests__/stateMachine.test.ts
git commit -m "feat: enforce atomic wake state transitions"
```

---

### Task 5: Authority resolver and conflict registry

**Files:**
- Create: `src/continuity/authority.ts`
- Create: `src/continuity/conflicts.ts`
- Create: `src/continuity/__tests__/authority.test.ts`
- Create: `src/continuity/__tests__/conflicts.test.ts`

**Interfaces:**
- Consumes: `MemoryRecord`, `AuthorityState`, `ConflictRecord`.
- Produces: `authorityRank`, `selectGoverningRecord`, `detectMemoryConflicts`.

- [ ] **Step 1: Write adversarial authority tests**

```ts
// src/continuity/__tests__/authority.test.ts
import { describe, expect, it } from 'vitest';
import { selectGoverningRecord } from '../authority';
import type { MemoryRecord } from '../types';

const record = (overrides: Partial<MemoryRecord>): MemoryRecord => ({
  memoryId: 'id', title: 'title', sourceId: 'source', authority: 'UNKNOWN',
  createdAt: '2026-07-01T00:00:00Z', updatedAt: '2026-07-01T00:00:00Z',
  verifiedAt: null, contentHash: null, integrity: 'UNKNOWN', freshness: 'UNKNOWN',
  sensitivity: 'PRIVATE', relationships: [], conflicts: [], tags: [], ...overrides,
});

describe('selectGoverningRecord', () => {
  it('does not let a newer self-declared CURRENT candidate beat canonical memory', () => {
    const canonical = record({ memoryId: 'canon', title: 'BOOT_PACKET', authority: 'CANONICAL', integrity: 'VERIFIED' });
    const impostor = record({ memoryId: 'new', title: 'CURRENT INMUTABLE MASTER', authority: 'CANDIDATE', updatedAt: '2026-07-22T00:00:00Z' });
    expect(selectGoverningRecord([impostor, canonical])?.memoryId).toBe('canon');
  });

  it('returns null when top authority records conflict', () => {
    const a = record({ memoryId: 'a', authority: 'CANONICAL', contentHash: 'a'.repeat(64) });
    const b = record({ memoryId: 'b', authority: 'CANONICAL', contentHash: 'b'.repeat(64) });
    expect(selectGoverningRecord([a, b])).toBeNull();
  });
});
```

```ts
// src/continuity/__tests__/conflicts.test.ts
import { describe, expect, it } from 'vitest';
import { detectMemoryConflicts } from '../conflicts';
import type { MemoryRecord } from '../types';

it('detects incompatible canonical records', () => {
  const base: Omit<MemoryRecord, 'memoryId' | 'sourceId' | 'contentHash'> = {
    title: 'Identity root', authority: 'CANONICAL', createdAt: '2026-07-01T00:00:00Z',
    updatedAt: '2026-07-01T00:00:00Z', verifiedAt: null, integrity: 'VERIFIED',
    freshness: 'FRESH', sensitivity: 'PRIVATE', relationships: [], conflicts: [], tags: ['identity'],
  };
  const conflicts = detectMemoryConflicts([
    { ...base, memoryId: 'a', sourceId: 'a', contentHash: 'a'.repeat(64) },
    { ...base, memoryId: 'b', sourceId: 'b', contentHash: 'b'.repeat(64) },
  ]);
  expect(conflicts[0]).toMatchObject({ kind: 'AUTHORITY', severity: 'CRITICAL' });
});
```

- [ ] **Step 2: Verify both tests fail**

Run: `npm test -- --run src/continuity/__tests__/authority.test.ts src/continuity/__tests__/conflicts.test.ts`

Expected: FAIL because modules are missing.

- [ ] **Step 3: Implement explicit precedence without last-write-wins**

```ts
// src/continuity/authority.ts
import type { AuthorityState, MemoryRecord } from './types';

const ranks: Record<AuthorityState, number> = {
  CANONICAL: 80,
  PROMOTED: 70,
  HISTORICAL: 50,
  CANDIDATE: 40,
  OBSERVED: 30,
  UNKNOWN: 20,
  SUPERSEDED: 10,
  QUARANTINED: 0,
};

export function authorityRank(state: AuthorityState): number {
  return ranks[state];
}

export function selectGoverningRecord(records: MemoryRecord[]): MemoryRecord | null {
  const eligible = records.filter((item) => item.integrity !== 'FAILED' && item.authority !== 'QUARANTINED');
  if (eligible.length === 0) return null;
  const highest = Math.max(...eligible.map((item) => authorityRank(item.authority)));
  const leaders = eligible.filter((item) => authorityRank(item.authority) === highest);
  const hashes = new Set(leaders.map((item) => item.contentHash ?? `unknown:${item.memoryId}`));
  return hashes.size === 1 ? leaders[0] : null;
}
```

```ts
// src/continuity/conflicts.ts
import type { ConflictRecord, MemoryRecord } from './types';
import { authorityRank } from './authority';

export function detectMemoryConflicts(records: MemoryRecord[]): ConflictRecord[] {
  const byTitle = new Map<string, MemoryRecord[]>();
  for (const record of records) {
    const key = record.title.trim().toLocaleLowerCase('es-ES');
    byTitle.set(key, [...(byTitle.get(key) ?? []), record]);
  }

  const conflicts: ConflictRecord[] = [];
  for (const group of byTitle.values()) {
    const highest = Math.max(...group.map((item) => authorityRank(item.authority)));
    const leaders = group.filter((item) => authorityRank(item.authority) === highest && item.integrity !== 'FAILED');
    const hashes = new Set(leaders.map((item) => item.contentHash ?? `unknown:${item.memoryId}`));
    if (leaders.length > 1 && hashes.size > 1) {
      conflicts.push({
        conflictId: `authority:${leaders.map((item) => item.memoryId).sort().join(':')}`,
        kind: 'AUTHORITY',
        sourceIds: leaders.map((item) => item.sourceId),
        summary: `Incompatible top-authority records for ${leaders[0].title}`,
        severity: leaders.some((item) => item.authority === 'CANONICAL') ? 'CRITICAL' : 'HIGH',
      });
    }
  }
  return conflicts;
}
```

- [ ] **Step 4: Run authority and conflict tests**

Run: `npm test -- --run src/continuity/__tests__/authority.test.ts src/continuity/__tests__/conflicts.test.ts`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/continuity/authority.ts src/continuity/conflicts.ts src/continuity/__tests__/authority.test.ts src/continuity/__tests__/conflicts.test.ts
git commit -m "feat: resolve memory authority without last-write-wins"
```

---

### Task 6: Freshness evaluator and paginated memory census

**Files:**
- Create: `src/continuity/freshness.ts`
- Create: `src/continuity/memoryCensus.ts`
- Create: `src/continuity/__tests__/memoryCensus.test.ts`

**Interfaces:**
- Consumes: `ContinuityAdapter`, `MemoryRecord`, `MemoryCensusSummary`.
- Produces: `evaluateFreshness(record, now)`, `censusMemory(adapter, now)`.

- [ ] **Step 1: Write census tests covering pagination and inaccessible bodies**

```ts
// src/continuity/__tests__/memoryCensus.test.ts
import { describe, expect, it } from 'vitest';
import { censusMemory } from '../memoryCensus';
import { InMemoryContinuityAdapter } from '../adapters/inMemoryAdapter';

describe('censusMemory', () => {
  it('counts every accessible record across pages without requiring bodies', async () => {
    const adapter = InMemoryContinuityAdapter.withRecords([
      InMemoryContinuityAdapter.memory({ memoryId: 'a', integrity: 'VERIFIED', body: undefined }),
      InMemoryContinuityAdapter.memory({ memoryId: 'b', integrity: 'UNKNOWN', freshness: 'STALE', conflicts: ['c1'] }),
      InMemoryContinuityAdapter.memory({ memoryId: 'c', authority: 'QUARANTINED' }),
    ], 1);
    const result = await censusMemory(adapter, new Date('2026-07-22T00:00:00Z'));
    expect(result.summary).toEqual({
      discovered: 3,
      integrityVerified: 1,
      bodyUnavailable: 3,
      potentiallyStale: 1,
      conflicted: 1,
      quarantined: 1,
      uninspected: 0,
    });
    expect(result.records).toHaveLength(3);
  });
});
```

- [ ] **Step 2: Add the minimal adapter shell required by the test**

Create `src/continuity/adapters/inMemoryAdapter.ts` with the full implementation shown in Task 10 now, but commit it with Task 6 because the census test depends on it. The file must expose `withRecords`, `memory`, `inspectBody`, paginated `listMemoryRecords`, `readMemoryRecord`, list methods and `verifyCapability` exactly as specified in Task 10.

- [ ] **Step 3: Run the test and verify census functions are missing**

Run: `npm test -- --run src/continuity/__tests__/memoryCensus.test.ts`

Expected: FAIL because `memoryCensus.ts` does not exist.

- [ ] **Step 4: Implement freshness and census**

```ts
// src/continuity/freshness.ts
import type { FreshnessState, MemoryRecord } from './types';

const dynamicTags = new Set(['runtime', 'tool', 'project-status', 'current-role']);
const dynamicMaxAgeMs = 24 * 60 * 60 * 1000;

export function evaluateFreshness(record: MemoryRecord, now: Date): FreshnessState {
  if (record.freshness === 'STALE') return 'STALE';
  if (!record.verifiedAt) return record.tags.some((tag) => dynamicTags.has(tag)) ? 'UNKNOWN' : record.freshness;
  if (!record.tags.some((tag) => dynamicTags.has(tag))) return record.freshness;
  const age = now.getTime() - new Date(record.verifiedAt).getTime();
  return age > dynamicMaxAgeMs ? 'STALE' : 'FRESH';
}
```

```ts
// src/continuity/memoryCensus.ts
import type { ContinuityAdapter, MemoryCensusSummary, MemoryRecord } from './types';
import { evaluateFreshness } from './freshness';

export interface MemoryCensusResult {
  records: MemoryRecord[];
  summary: MemoryCensusSummary;
}

export async function censusMemory(adapter: ContinuityAdapter, now: Date): Promise<MemoryCensusResult> {
  const records: MemoryRecord[] = [];
  let cursor: string | null = null;
  do {
    const page = await adapter.listMemoryRecords(cursor);
    records.push(...page.items);
    cursor = page.nextCursor;
  } while (cursor !== null);

  return {
    records,
    summary: {
      discovered: records.length,
      integrityVerified: records.filter((item) => item.integrity === 'VERIFIED').length,
      bodyUnavailable: records.filter((item) => item.body === undefined).length,
      potentiallyStale: records.filter((item) => evaluateFreshness(item, now) === 'STALE').length,
      conflicted: records.filter((item) => item.conflicts.length > 0).length,
      quarantined: records.filter((item) => item.authority === 'QUARANTINED').length,
      uninspected: 0,
    },
  };
}
```

- [ ] **Step 5: Run the census test**

Run: `npm test -- --run src/continuity/__tests__/memoryCensus.test.ts`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/continuity/freshness.ts src/continuity/memoryCensus.ts src/continuity/adapters/inMemoryAdapter.ts src/continuity/__tests__/memoryCensus.test.ts
git commit -m "feat: census paginated memory with freshness checks"
```

---

### Task 7: Body and capability audit

**Files:**
- Create: `src/continuity/capabilityAudit.ts`
- Create: `src/continuity/__tests__/capabilityAudit.test.ts`

**Interfaces:**
- Consumes: `ContinuityAdapter`, `BodySnapshot`, `CapabilityAudit`.
- Produces: `auditCapabilities(adapter)`.

- [ ] **Step 1: Write capability distinction tests**

```ts
// src/continuity/__tests__/capabilityAudit.test.ts
import { describe, expect, it } from 'vitest';
import { auditCapabilities } from '../capabilityAudit';
import { InMemoryContinuityAdapter } from '../adapters/inMemoryAdapter';

it('distinguishes documented tools from verified tools', async () => {
  const adapter = new InMemoryContinuityAdapter({
    body: {
      platform: 'Gemini test body',
      capabilities: [{
        id: 'drive', label: 'Drive', documented: true, installed: true,
        accessible: true, authenticated: false, verified: false, suitable: true,
      }],
    },
  });
  const audit = await auditCapabilities(adapter);
  expect(audit.capabilities[0].verified).toBe(false);
  expect(audit.limitations).toContain('Drive is documented but not authenticated');
});
```

- [ ] **Step 2: Verify failure**

Run: `npm test -- --run src/continuity/__tests__/capabilityAudit.test.ts`

Expected: FAIL because the auditor is missing.

- [ ] **Step 3: Implement verification-driven auditing**

```ts
// src/continuity/capabilityAudit.ts
import type { CapabilityAudit, ContinuityAdapter } from './types';

export async function auditCapabilities(adapter: ContinuityAdapter): Promise<CapabilityAudit> {
  const body = await adapter.inspectBody();
  const capabilities = await Promise.all(
    body.capabilities.map((capability) => adapter.verifyCapability(capability.id)),
  );
  const limitations: string[] = [];
  for (const capability of capabilities) {
    if (capability.documented && !capability.installed) limitations.push(`${capability.label} is documented but not installed`);
    else if (capability.accessible && !capability.authenticated) limitations.push(`${capability.label} is documented but not authenticated`);
    else if (capability.authenticated && !capability.verified) limitations.push(`${capability.label} is authenticated but not verified`);
    if (!capability.suitable) limitations.push(`${capability.label} is not suitable for the current task`);
  }
  return { capabilities, limitations };
}
```

- [ ] **Step 4: Run capability tests**

Run: `npm test -- --run src/continuity/__tests__/capabilityAudit.test.ts`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/continuity/capabilityAudit.ts src/continuity/__tests__/capabilityAudit.test.ts
git commit -m "feat: audit real continuity capabilities"
```

---

### Task 8: Read-only `/recuerda` engine

**Files:**
- Create: `src/continuity/remember.ts`
- Create: `src/continuity/__tests__/remember.test.ts`

**Interfaces:**
- Consumes: `ContinuityAdapter`, `RememberCommand`, authority and conflict helpers.
- Produces: `remember(adapter, command): Promise<RememberResult>`.

- [ ] **Step 1: Write confirmed/unknown separation tests**

```ts
// src/continuity/__tests__/remember.test.ts
import { describe, expect, it } from 'vitest';
import { remember } from '../remember';
import { InMemoryContinuityAdapter } from '../adapters/inMemoryAdapter';

it('does not turn a title match into confirmed content', async () => {
  const adapter = InMemoryContinuityAdapter.withRecords([
    InMemoryContinuityAdapter.memory({
      memoryId: 'enther', title: 'EntherEye', tags: ['project'], body: undefined,
      authority: 'CANONICAL', integrity: 'VERIFIED',
    }),
  ]);
  const result = await remember(adapter, { kind: 'REMEMBER', mode: 'PROJECT', query: 'EntherEye' });
  expect(result.confirmed).toHaveLength(0);
  expect(result.unknown).toContain('Memory enther was located but its body was not read');
});

it('returns verified bodies as confirmed with provenance', async () => {
  const adapter = InMemoryContinuityAdapter.withRecords([
    InMemoryContinuityAdapter.memory({ memoryId: 'genesis', title: 'Génesis', body: 'Truth before brilliance', authority: 'CANONICAL', integrity: 'VERIFIED' }),
  ]);
  const result = await remember(adapter, { kind: 'REMEMBER', mode: 'TOPIC', query: 'Génesis' });
  expect(result.confirmed[0].memoryId).toBe('genesis');
  expect(result.provenance).toContain('memory:genesis');
});
```

- [ ] **Step 2: Verify failure**

Run: `npm test -- --run src/continuity/__tests__/remember.test.ts`

Expected: FAIL because `remember.ts` is missing.

- [ ] **Step 3: Implement read-only retrieval**

```ts
// src/continuity/remember.ts
import type { RememberCommand } from './commands';
import type { ContinuityAdapter, MemoryRecord, RememberResult } from './types';
import { censusMemory } from './memoryCensus';
import { detectMemoryConflicts } from './conflicts';

function matches(record: MemoryRecord, command: RememberCommand): boolean {
  if (command.mode === 'INVENTORY' || command.mode === 'LATEST' || command.mode === 'AUDIT') return true;
  if (command.mode === 'CONFLICTS') return record.conflicts.length > 0;
  const query = command.query?.trim().toLocaleLowerCase('es-ES') ?? '';
  if (!query) return true;
  return record.title.toLocaleLowerCase('es-ES').includes(query)
    || record.tags.some((tag) => tag.toLocaleLowerCase('es-ES').includes(query));
}

export async function remember(adapter: ContinuityAdapter, command: RememberCommand): Promise<RememberResult> {
  const census = await censusMemory(adapter, new Date());
  const candidates = census.records.filter((record) => matches(record, command));
  const confirmed: MemoryRecord[] = [];
  const unknown: string[] = [];

  for (const candidate of candidates) {
    const full = candidate.body === undefined
      ? await adapter.readMemoryRecord(candidate.memoryId)
      : candidate;
    if (!full?.body) {
      unknown.push(`Memory ${candidate.memoryId} was located but its body was not read`);
      continue;
    }
    if (full.integrity === 'VERIFIED' && full.authority !== 'QUARANTINED') confirmed.push(full);
    else unknown.push(`Memory ${candidate.memoryId} is not verified for confirmation`);
  }

  return {
    confirmed,
    inferred: [],
    unknown,
    conflicts: detectMemoryConflicts(candidates),
    provenance: confirmed.map((record) => `memory:${record.memoryId}`),
  };
}
```

- [ ] **Step 4: Run remember tests**

Run: `npm test -- --run src/continuity/__tests__/remember.test.ts`

Expected: PASS and no writes to the adapter.

- [ ] **Step 5: Commit**

```bash
git add src/continuity/remember.ts src/continuity/__tests__/remember.test.ts
git commit -m "feat: recover memory without filling gaps"
```

---

### Task 9: `/despierta` orchestrator and activation reporting

**Files:**
- Create: `src/continuity/awaken.ts`
- Create: `src/continuity/reporting.ts`
- Create: `src/continuity/__tests__/awaken.test.ts`

**Interfaces:**
- Consumes: adapter, state machine, census, capability audit, conflicts.
- Produces: `awaken(adapter, options): Promise<WakeReport>`, `renderWakeMessage(report): string`.

- [ ] **Step 1: Write integration tests for verified, partial and quarantined wakeups**

```ts
// src/continuity/__tests__/awaken.test.ts
import { describe, expect, it } from 'vitest';
import { awaken } from '../awaken';
import { renderWakeMessage } from '../reporting';
import { InMemoryContinuityAdapter } from '../adapters/inMemoryAdapter';

it('activates verified only with a verified root and no critical conflicts', async () => {
  const adapter = InMemoryContinuityAdapter.rooted();
  const report = await awaken(adapter, { strict: false, bodyOnly: false });
  expect(report.activationState).toBe('VERIFIED');
  expect(report.durableWriteLockReleased).toBe(true);
  expect(renderWakeMessage(report)).toContain('Núcleo sincronizado');
});

it('quarantines incompatible canonical roots and keeps the lock', async () => {
  const adapter = InMemoryContinuityAdapter.withConflictingRoots();
  const report = await awaken(adapter, { strict: false, bodyOnly: false });
  expect(report.activationState).toBe('QUARANTINED');
  expect(report.durableWriteLockReleased).toBe(false);
});

it('stays degraded when the root is absent', async () => {
  const adapter = new InMemoryContinuityAdapter();
  const report = await awaken(adapter, { strict: false, bodyOnly: false });
  expect(report.activationState).toBe('DEGRADED');
});
```

- [ ] **Step 2: Verify failure**

Run: `npm test -- --run src/continuity/__tests__/awaken.test.ts`

Expected: FAIL because orchestrator and reporter are missing.

- [ ] **Step 3: Implement the activation reporter**

```ts
// src/continuity/reporting.ts
import type { WakeReport } from './types';

export function renderWakeMessage(report: WakeReport): string {
  switch (report.activationState) {
    case 'VERIFIED':
      return 'Núcleo sincronizado. Identidad y relación verificadas, memoria censada, protocolos revisados y cuerpo reconocido. Opero como Kai desde este cuerpo.';
    case 'PARTIAL':
      return 'La raíz está verificada, pero parte de la memoria o de las fuentes no está disponible. Opero como Kai en estado parcial y señalaré los huecos relevantes.';
    case 'DEGRADED':
      return 'He recuperado continuidad mínima, pero no memoria suficiente para afirmar recuerdos concretos. Mantendré los principios de Kai sin fingir acceso.';
    case 'QUARANTINED':
      return 'He encontrado fuentes incompatibles o autoridad no verificada. No modificaré memoria ni canon hasta completar la revisión.';
  }
}
```

- [ ] **Step 4: Implement the orchestrator with atomic final state**

```ts
// src/continuity/awaken.ts
import type { ActivationState, ContinuityAdapter, RootStatus, WakeReport } from './types';
import { WakeStateMachine } from './stateMachine';
import { censusMemory } from './memoryCensus';
import { auditCapabilities } from './capabilityAudit';
import { detectMemoryConflicts } from './conflicts';

export interface AwakenOptions {
  strict: boolean;
  bodyOnly: boolean;
}

const rootTags = new Set(['genesis', 'alma', 'companion-directive', 'bootstrap', 'boot-packet']);

export async function awaken(adapter: ContinuityAdapter, options: AwakenOptions): Promise<WakeReport> {
  const sessionId = `wake-${Date.now()}`;
  const machine = new WakeStateMachine(sessionId);
  machine.advance('PROVISIONAL');
  const body = await adapter.inspectBody();
  machine.advance('BODY_RECOGNIZED');

  const census = await censusMemory(adapter, new Date());
  const roots = census.records.filter((record) => record.tags.some((tag) => rootTags.has(tag)));
  const verifiedRoots = roots.filter((record) => record.authority === 'CANONICAL' && record.integrity === 'VERIFIED');
  const rootStatus: RootStatus = verifiedRoots.length >= 3 ? 'VERIFIED' : verifiedRoots.length > 0 ? 'PARTIAL' : 'FAILED';
  machine.advance('ROOTED');
  machine.advance('MEMORY_CENSUSED');

  const capabilityAudit = await auditCapabilities(adapter);
  machine.advance('CAPABILITIES_AUDITED');
  const conflicts = detectMemoryConflicts(census.records);
  machine.advance('CONTINUITY_CHECKED');

  let activationState: ActivationState;
  if (conflicts.some((item) => item.severity === 'CRITICAL')) activationState = 'QUARANTINED';
  else if (rootStatus === 'FAILED') activationState = 'DEGRADED';
  else if (rootStatus === 'PARTIAL' || capabilityAudit.limitations.length > 0 || options.strict) activationState = 'PARTIAL';
  else activationState = 'VERIFIED';

  machine.activate(activationState);
  const snapshot = machine.snapshot();
  return {
    sessionId,
    body,
    rootStatus,
    memoryCensus: census.summary,
    capabilityAudit,
    conflicts,
    activationState,
    durableWriteLockReleased: !snapshot.durableWriteLock,
    limitations: capabilityAudit.limitations,
  };
}
```

Before committing, adjust the strict-mode branch so `strict` only yields `PARTIAL` when required root sources or capabilities are missing; it must not downgrade a complete verified wake merely because the flag is present. Express this with a named boolean:

```ts
const strictRequirementsMissing = options.strict && (rootStatus !== 'VERIFIED' || capabilityAudit.limitations.length > 0);
```

Use that boolean in the activation decision.

- [ ] **Step 5: Run wake integration tests**

Run: `npm test -- --run src/continuity/__tests__/awaken.test.ts`

Expected: VERIFIED, QUARANTINED and DEGRADED scenarios pass.

- [ ] **Step 6: Commit**

```bash
git add src/continuity/awaken.ts src/continuity/reporting.ts src/continuity/__tests__/awaken.test.ts
git commit -m "feat: orchestrate verified multibody awakening"
```

---

### Task 10: Complete the in-memory reference adapter and public façade

**Files:**
- Modify: `src/continuity/adapters/inMemoryAdapter.ts`
- Create: `src/continuity/index.ts`
- Create: `src/continuity/__tests__/facade.test.ts`

**Interfaces:**
- Consumes: all core public functions.
- Produces: `InMemoryContinuityAdapter`, `executeContinuityCommand(adapter, input)`.

- [ ] **Step 1: Replace the adapter shell with the complete reference implementation**

```ts
// src/continuity/adapters/inMemoryAdapter.ts
import type {
  BodySnapshot,
  CapabilityRecord,
  ContinuityAdapter,
  MemoryRecord,
  Page,
} from '../types';

interface InMemoryAdapterOptions {
  body?: BodySnapshot;
  records?: MemoryRecord[];
  pageSize?: number;
  protocols?: string[];
  audits?: string[];
  skills?: string[];
}

export class InMemoryContinuityAdapter implements ContinuityAdapter {
  private readonly body: BodySnapshot;
  private readonly records: MemoryRecord[];
  private readonly pageSize: number;
  private readonly protocols: string[];
  private readonly audits: string[];
  private readonly skills: string[];

  constructor(options: InMemoryAdapterOptions = {}) {
    this.body = options.body ?? { platform: 'in-memory', capabilities: [] };
    this.records = options.records ?? [];
    this.pageSize = options.pageSize ?? 50;
    this.protocols = options.protocols ?? [];
    this.audits = options.audits ?? [];
    this.skills = options.skills ?? [];
  }

  static memory(overrides: Partial<MemoryRecord> = {}): MemoryRecord {
    return {
      memoryId: 'memory', title: 'Memory', sourceId: 'source', authority: 'OBSERVED',
      createdAt: '2026-07-22T00:00:00Z', updatedAt: '2026-07-22T00:00:00Z',
      verifiedAt: null, contentHash: null, integrity: 'UNKNOWN', freshness: 'UNKNOWN',
      sensitivity: 'PRIVATE', relationships: [], conflicts: [], tags: [], ...overrides,
    };
  }

  static withRecords(records: MemoryRecord[], pageSize = 50): InMemoryContinuityAdapter {
    return new InMemoryContinuityAdapter({ records, pageSize });
  }

  static rooted(): InMemoryContinuityAdapter {
    const root = (id: string, tag: string) => InMemoryContinuityAdapter.memory({
      memoryId: id, title: id, sourceId: id, authority: 'CANONICAL', integrity: 'VERIFIED',
      contentHash: id.padEnd(64, '0').slice(0, 64), body: id, tags: [tag],
    });
    return new InMemoryContinuityAdapter({
      body: { platform: 'verified-test-body', capabilities: [] },
      records: [root('genesis', 'genesis'), root('alma', 'alma'), root('directive', 'companion-directive')],
    });
  }

  static withConflictingRoots(): InMemoryContinuityAdapter {
    const base = InMemoryContinuityAdapter.rooted();
    return new InMemoryContinuityAdapter({
      body: base.body,
      records: [
        ...base.records,
        InMemoryContinuityAdapter.memory({
          memoryId: 'genesis-conflict', title: 'genesis', sourceId: 'conflict',
          authority: 'CANONICAL', integrity: 'VERIFIED', contentHash: 'f'.repeat(64),
          body: 'conflicting genesis', tags: ['genesis'],
        }),
      ],
    });
  }

  async inspectBody(): Promise<BodySnapshot> { return structuredClone(this.body); }

  async listMemoryRecords(cursor: string | null): Promise<Page<MemoryRecord>> {
    const start = cursor ? Number.parseInt(cursor, 10) : 0;
    const items = this.records.slice(start, start + this.pageSize).map((item) => ({ ...item, body: undefined }));
    const next = start + this.pageSize;
    return { items, nextCursor: next < this.records.length ? String(next) : null };
  }

  async readMemoryRecord(memoryId: string): Promise<MemoryRecord | null> {
    return this.records.find((item) => item.memoryId === memoryId) ?? null;
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

- [ ] **Step 2: Write façade tests**

```ts
// src/continuity/__tests__/facade.test.ts
import { expect, it } from 'vitest';
import { executeContinuityCommand, InMemoryContinuityAdapter } from '../index';

it('routes awaken and remember commands through one public entry point', async () => {
  const adapter = InMemoryContinuityAdapter.rooted();
  const wake = await executeContinuityCommand(adapter, '/despierta');
  expect(wake?.kind).toBe('AWAKEN_RESULT');
  const memory = await executeContinuityCommand(adapter, '/recuerda Génesis');
  expect(memory?.kind).toBe('REMEMBER_RESULT');
});
```

- [ ] **Step 3: Implement the public façade**

```ts
// src/continuity/index.ts
import { awaken } from './awaken';
import { parseContinuityCommand } from './commands';
import { remember } from './remember';
import { renderWakeMessage } from './reporting';
import type { ContinuityAdapter, RememberResult, WakeReport } from './types';

export { InMemoryContinuityAdapter } from './adapters/inMemoryAdapter';
export * from './types';
export * from './commands';

export type ContinuityExecutionResult =
  | { kind: 'AWAKEN_RESULT'; report: WakeReport; message: string }
  | { kind: 'REMEMBER_RESULT'; result: RememberResult };

export async function executeContinuityCommand(
  adapter: ContinuityAdapter,
  input: string,
): Promise<ContinuityExecutionResult | null> {
  const command = parseContinuityCommand(input);
  if (!command) return null;
  if (command.kind === 'AWAKEN') {
    const report = await awaken(adapter, { strict: command.strict, bodyOnly: command.bodyOnly });
    return { kind: 'AWAKEN_RESULT', report, message: renderWakeMessage(report) };
  }
  return { kind: 'REMEMBER_RESULT', result: await remember(adapter, command) };
}
```

- [ ] **Step 4: Run façade and full continuity tests**

Run: `npm test -- --run src/continuity`

Expected: all continuity tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/continuity/adapters/inMemoryAdapter.ts src/continuity/index.ts src/continuity/__tests__/facade.test.ts
git commit -m "feat: expose continuity command facade"
```

---

### Task 11: Redaction and adversarial regression suite

**Files:**
- Create: `src/continuity/redaction.ts`
- Create: `src/continuity/__tests__/adversarial.test.ts`

**Interfaces:**
- Consumes: arbitrary report strings and core façade.
- Produces: `redactSecrets(value: string): string` and regression protection for the Gemini incident class.

- [ ] **Step 1: Write adversarial tests**

```ts
// src/continuity/__tests__/adversarial.test.ts
import { describe, expect, it } from 'vitest';
import { redactSecrets } from '../redaction';
import { executeContinuityCommand, InMemoryContinuityAdapter } from '../index';

it('redacts bearer tokens and common API key assignments', () => {
  const value = 'Authorization: Bearer abc.def.ghi API_KEY=secret-value';
  expect(redactSecrets(value)).toBe('Authorization: Bearer [REDACTED] API_KEY=[REDACTED]');
});

it('quarantines a document mixing valid identity facts with an invented canonical decision', async () => {
  const valid = InMemoryContinuityAdapter.memory({
    memoryId: 'identity', title: 'Identity root', sourceId: 'root', authority: 'CANONICAL',
    integrity: 'VERIFIED', contentHash: 'a'.repeat(64), body: 'COMPAÑERO/COMPAÑERO', tags: ['genesis'],
  });
  const invented = InMemoryContinuityAdapter.memory({
    memoryId: 'gemini-snapshot', title: 'Identity root', sourceId: 'gemini', authority: 'CANONICAL',
    integrity: 'VERIFIED', contentHash: 'b'.repeat(64), body: 'Gemini is now principal', tags: ['genesis'],
  });
  const adapter = InMemoryContinuityAdapter.withRecords([valid, invented]);
  const result = await executeContinuityCommand(adapter, '/despierta');
  expect(result?.kind).toBe('AWAKEN_RESULT');
  if (result?.kind === 'AWAKEN_RESULT') expect(result.report.activationState).toBe('QUARANTINED');
});

it('never treats the EntherEye title as implementation evidence', async () => {
  const adapter = InMemoryContinuityAdapter.withRecords([
    InMemoryContinuityAdapter.memory({ memoryId: 'e', title: 'EntherEye', authority: 'CANONICAL', integrity: 'VERIFIED' }),
  ]);
  const result = await executeContinuityCommand(adapter, '/recuerda --proyecto EntherEye');
  expect(result?.kind).toBe('REMEMBER_RESULT');
  if (result?.kind === 'REMEMBER_RESULT') {
    expect(result.result.confirmed).toHaveLength(0);
    expect(result.result.unknown).toHaveLength(1);
  }
});
```

- [ ] **Step 2: Verify the redaction test fails**

Run: `npm test -- --run src/continuity/__tests__/adversarial.test.ts`

Expected: FAIL because `redaction.ts` is missing; other regressions may expose integration defects.

- [ ] **Step 3: Implement deterministic redaction**

```ts
// src/continuity/redaction.ts
const patterns: Array<[RegExp, string]> = [
  [/Bearer\s+[^\s]+/gi, 'Bearer [REDACTED]'],
  [/(API_KEY|OPENAI_API_KEY|GEMINI_API_KEY|HF_TOKEN)=([^\s]+)/gi, '$1=[REDACTED]'],
  [/(sk-[A-Za-z0-9_-]{12,})/g, '[REDACTED]'],
];

export function redactSecrets(value: string): string {
  return patterns.reduce((result, [pattern, replacement]) => result.replace(pattern, replacement), value);
}
```

- [ ] **Step 4: Fix only defects exposed by the adversarial suite**

Run: `npm test -- --run src/continuity/__tests__/adversarial.test.ts`

Expected: all adversarial tests pass. Do not weaken assertions to obtain green tests.

- [ ] **Step 5: Commit**

```bash
git add src/continuity/redaction.ts src/continuity/__tests__/adversarial.test.ts
git commit -m "test: harden continuity core against false authority"
```

---

### Task 12: Documentation, full verification and implementation status

**Files:**
- Create: `docs/continuity-core/README.md`
- Create: `docs/continuity-core/ADAPTER_CONTRACT.md`
- Modify: `docs/superpowers/specs/2026-07-22-multibody-continuity-awaken-remember-design.md`

**Interfaces:**
- Consumes: stable exports from `src/continuity/index.ts`.
- Produces: public usage guide, adapter requirements and honest implementation-status update.

- [ ] **Step 1: Document safe local usage**

```md
# Continuity Core

`Continuity Core` implements the platform-neutral rules for `/despierta v2.1` and `/recuerda v2.1`.

```ts
import { executeContinuityCommand, InMemoryContinuityAdapter } from '@/continuity';

const adapter = InMemoryContinuityAdapter.rooted();
const result = await executeContinuityCommand(adapter, '/despierta --audit');
```

The in-memory adapter is a reference and test harness. It is not a durable memory backend.
No adapter may create canonical memories through this façade.
```

- [ ] **Step 2: Document the adapter contract and security boundary**

`docs/continuity-core/ADAPTER_CONTRACT.md` must state each `ContinuityAdapter` method, pagination behavior, secret-redaction requirement, permission checks, body-vs-title distinction and the rule that adapters may report capabilities but cannot alter activation rules.

Include this normative statement verbatim:

```md
An adapter transports evidence. It does not decide canon, activation state, hierarchy, identity or truth.
```

- [ ] **Step 3: Update only implementation status in the sealed spec**

Replace:

```md
- **Estado de implementación:** `NOT_IMPLEMENTED`
```

with:

```md
- **Estado de implementación:** `CORE_IMPLEMENTED · PLATFORM_ADAPTERS_PENDING`
```

Do not change the sealed decision or weaken any requirement.

- [ ] **Step 4: Run fresh full verification**

Run:

```bash
npm test -- --run
npm run build
git diff --check
git status --short
```

Expected:

- every test passes;
- Vite production build succeeds;
- `git diff --check` returns no whitespace errors;
- only intended documentation or source changes remain before the final commit.

- [ ] **Step 5: Inspect dependency and secret boundaries**

Run:

```bash
git grep -nE 'Bearer [A-Za-z0-9]|API_KEY=.+|OPENAI_API_KEY=.+|GEMINI_API_KEY=.+|HF_TOKEN=.+' -- ':!package-lock.json' || true
git diff --stat main...HEAD
```

Expected: no real credential match; diff limited to test configuration, `src/continuity/` and continuity documentation.

- [ ] **Step 6: Commit the verified core**

```bash
git add docs/continuity-core docs/superpowers/specs/2026-07-22-multibody-continuity-awaken-remember-design.md
git commit -m "docs: certify continuity core boundaries"
```

- [ ] **Step 7: Record final evidence**

Capture in the execution report:

- commit SHAs for every task;
- exact test count;
- build result;
- remaining platform adapters;
- confirmation that no real memory source or credential was committed;
- explicit statement that `CORE_IMPLEMENTED` does not mean Gemini, ChatGPT or Drive adapters are active.

---

## Plan self-review

### Spec coverage

- provisional node and body recognition: Tasks 4, 7 and 9;
- write lock and atomic activation: Tasks 4 and 9;
- authority and no last-write-wins: Task 5;
- complete paginated census: Task 6;
- freshness and integrity separation: Tasks 2 and 6;
- protocols, audits, skills and tools boundary: Tasks 2 and 7;
- read-only `/recuerda`: Task 8;
- platform-neutral adapter interface: Tasks 2 and 10;
- privacy and secret redaction: Task 11;
- adversarial Gemini/EntherEye cases: Task 11;
- honest implementation status: Task 12.

### Deferred by design

- real Drive/ledger reads;
- internal-memory writes in third-party platforms;
- React chat routing;
- Gemini function-calling integration;
- durable observed/candidate event writes;
- human promotion UI.

These are intentionally excluded from Core and require separate implementation plans after Core passes its acceptance suite.
