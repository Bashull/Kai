import { spawn } from 'node:child_process';
import type { ProcessExecutor, ProcessResult } from './ffmpegRuntime';

export interface NodeProcessExecutorOptions {
  timeoutMs?: number;
  maxStdoutChars?: number;
  maxStderrChars?: number;
}

export function createNodeProcessExecutor(
  options: NodeProcessExecutorOptions = {},
): ProcessExecutor {
  const timeoutMs = options.timeoutMs ?? 120_000;
  const maxStdout = options.maxStdoutChars ?? 1_000_000;
  const maxStderr = options.maxStderrChars ?? 8_000;

  return (bin: string, args: string[]): Promise<ProcessResult> =>
    new Promise((resolve) => {
      let stdout = '';
      let stderr = '';
      let settled = false;
      const child = spawn(bin, args, { shell: false });

      const finish = (result: ProcessResult): void => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve(result);
      };
      child.stdout?.on('data', (chunk: Buffer) => {
        stdout = (stdout + chunk.toString()).slice(-maxStdout);
      });
      child.stderr?.on('data', (chunk: Buffer) => {
        stderr = (stderr + chunk.toString()).slice(-maxStderr);
      });
      child.on('close', (code) => finish({ code, stdout, stderr }));
      child.on('error', (error) =>
        finish({ code: -1, stdout, stderr: (stderr + String(error)).slice(-maxStderr) }),
      );

      const timer = setTimeout(() => {
        child.kill();
        finish({ code: -2, stdout, stderr: (stderr + 'PROCESS_TIMEOUT').slice(-maxStderr) });
      }, timeoutMs);
    });
}
