'use strict';

const os = require('node:os');
const crypto = require('node:crypto');
const { io } = require('socket.io-client');
const {
  validateRequestEnvelope,
  createResponseEnvelope,
} = require('../protocol/envelope');
const { createHmacProof } = require('../relay/auth');
const { authorizeAction } = require('./policy');
const { runCommand } = require('./commandRunner');
const { listDirectory, readFile, writeFileAtomic } = require('./fileOps');
const { listProcesses, killProcess } = require('./processOps');
const { AuditLog } = require('./audit');
const { KillSwitch } = require('./killSwitch');
const { startHeartbeat } = require('./heartbeat');

function createPcAgent(options) {
  const state = {
    connected: false,
    authenticated: false,
    stopped: false,
    lastHeartbeatAt: null,
  };

  const audit = new AuditLog(options.auditPath);
  const killSwitch = new KillSwitch(options.killSwitchPath);
  let socket = null;
  let stopHeartbeat = null;

  async function executeAction(envelope) {
    switch (envelope.action) {
      case 'ping':
        return { pong: true };
      case 'heartbeat':
        return { alive: true };
      case 'device_info':
        return {
          hostname: os.hostname(),
          platform: process.platform,
          arch: process.arch,
          node: process.version,
          pid: process.pid,
        };
      case 'list_processes':
        return listProcesses();
      case 'list_directory':
        return listDirectory(envelope.params, options.policy);
      case 'read_file':
        return readFile(envelope.params, options.policy);
      case 'write_file':
        return writeFileAtomic(envelope.params, options.policy);
      case 'run_command':
        return runCommand(envelope.params, options.policy);
      case 'kill_process':
        return killProcess(envelope.params.pid);
      case 'audit_log':
        return audit.read(envelope.params.limit ?? 100);
      default:
        return null;
    }
  }

  async function dispatch(envelope) {
    const startedAt = new Date().toISOString();
    const auditId = crypto.randomUUID();
    let status = 'ok';
    let result = null;
    let error = null;

    try {
      validateRequestEnvelope(envelope);
      await killSwitch.assertActive();

      const authz = authorizeAction(options.policy, envelope);
      if (!authz.allowed) {
        throw new Error(authz.reason);
      }

      if (envelope.action === 'kill_switch') {
        await killSwitch.trigger('remote_authenticated');
        state.stopped = true;
        result = { stopped: true };
      } else {
        result = await executeAction(envelope);
        if (result === null) {
          throw new Error(`Unhandled action: ${envelope.action}`);
        }
      }
    } catch (caught) {
      status = 'error';
      error = {
        code: caught.code ?? 'ACTION_FAILED',
        message: caught.message,
      };
    }

    const finishedAt = new Date().toISOString();
    await audit.append({
      audit_id: auditId,
      request_id: envelope?.request_id ?? null,
      session_id: envelope?.session_id ?? null,
      device_id: options.deviceId,
      actor_id: envelope?.actor_id ?? 'unknown',
      action: envelope?.action ?? null,
      capability: envelope?.capability ?? null,
      resource: envelope?.params?.path ?? envelope?.params?.executable ?? null,
      timestamp_start: startedAt,
      timestamp_end: finishedAt,
      status,
      error_code: error?.code ?? null,
    });

    return createResponseEnvelope({
      request_id: envelope?.request_id ?? null,
      status,
      started_at: startedAt,
      finished_at: finishedAt,
      result,
      error,
      audit_id: auditId,
    });
  }

  function emitAuthenticationProof() {
    const proofPayload = {
      device_id: options.deviceId,
      socket_id: socket.id,
    };
    socket.emit('agent:authenticate', {
      device_id: options.deviceId,
      proof_payload: proofPayload,
      proof: createHmacProof(options.deviceToken, proofPayload),
    });
  }

  async function start() {
    if (socket) {
      throw new Error('PC agent is already started');
    }

    state.stopped = false;
    socket = io(options.relayUrl, {
      autoConnect: false,
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: options.reconnectBaseMs ?? 500,
      reconnectionDelayMax: 30000,
      timeout: 5000,
    });

    socket.on('connect', () => {
      state.connected = true;
      state.authenticated = false;
      emitAuthenticationProof();
    });

    socket.on('disconnect', () => {
      state.connected = false;
      state.authenticated = false;
      stopHeartbeat?.();
      stopHeartbeat = null;
    });

    socket.on('agent:authenticated', () => {
      state.authenticated = true;
      stopHeartbeat?.();
      stopHeartbeat = startHeartbeat({
        intervalMs: options.heartbeatIntervalMs ?? 15000,
        send: payload => {
          state.lastHeartbeatAt = payload.timestamp;
          socket.emit('agent:heartbeat', payload);
        },
      });
    });

    socket.on('agent:error', payload => {
      if (payload?.error === 'AUTHENTICATION_FAILED') {
        state.authenticated = false;
      }
    });

    socket.on('agent:request', async envelope => {
      const response = await dispatch(envelope);
      socket.emit('agent:response', response);
      if (state.stopped) {
        await stop();
      }
    });

    const firstConnect = new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        cleanup();
        reject(new Error('Agent connection timeout'));
      }, options.connectTimeoutMs ?? 5000);

      const onConnect = () => {
        cleanup();
        resolve();
      };
      const onError = error => {
        cleanup();
        reject(error);
      };
      const cleanup = () => {
        clearTimeout(timer);
        socket.off('connect', onConnect);
        socket.off('connect_error', onError);
      };

      socket.once('connect', onConnect);
      socket.once('connect_error', onError);
    });

    socket.connect();
    await firstConnect;
  }

  async function stop() {
    stopHeartbeat?.();
    stopHeartbeat = null;

    if (socket) {
      socket.removeAllListeners();
      socket.disconnect();
      socket = null;
    }

    state.connected = false;
    state.authenticated = false;
    state.stopped = true;
  }

  return { start, stop, dispatch, state };
}

module.exports = { createPcAgent };
