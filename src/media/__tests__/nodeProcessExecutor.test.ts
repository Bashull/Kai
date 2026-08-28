import { describe, expect, it } from 'vitest';
import { createNodeProcessExecutor } from '../nodeProcessExecutor';

describe('createNodeProcessExecutor', () => {
  it('executes argv without a shell and captures stdout/stderr', async () => {
    const execute = createNodeProcessExecutor({ timeoutMs: 5000 });
    const result = await execute(process.execPath, [
      '-e',
      "process.stdout.write('ok'); process.stderr.write('warn')",
    ]);
    expect(result.code).toBe(0);
    expect(result.stdout).toBe('ok');
    expect(result.stderr).toBe('warn');
  });

  it('bounds captured stderr', async () => {
    const execute = createNodeProcessExecutor({ timeoutMs: 5000, maxStderrChars: 32 });
    const result = await execute(process.execPath, [
      '-e',
      "process.stderr.write('x'.repeat(100))",
    ]);
    expect(result.stderr.length).toBe(32);
  });
});
