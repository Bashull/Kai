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
const { writeCredentialsAtomic } = require('./credentials');

function createPcAgent(options) {
  const state = {
    connected: false,
    authenticated: false,
    stopped: false,
    lastHeartbeatAt: null,
    pairing: null,
    lastError: null,
  };

  const audit = new AuditLog(options.auditPath);
  const killSwitch = new KillSwitch(options.killSwitchPath);
  let socket = null;
  let stopHeartbeat = null;
  let deviceToken = options.deviceToken ?? null;
  const pairingCode = options.pairingCode ?? crypto.randomBytes(5).toString('base64url').slice(0, 8).toUpperCase();
  const publicIdentity = options.publicIdentity ?? `kai-pc-agent:${os.hostname()}:${options.deviceId}`;

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
    if (!deviceToken) throw new Error('Device token is not available');
    const proofPayload = {
      device_id: options.deviceId,
      socket_id: socket.id,
    };
    socket.emit('agent:authenticate', {
      device_id: options.deviceId,
      proof_payload: proofPayload,
      proof: createHmacProof(deviceToken, proofPayload),
    });
  }

  function announcePairing() {
    socket.emit('agent:announce-pairing', {
      device_id: options.deviceId,
      code: pairingCode,
      public_identity: publicIdentity,
      ttl_ms: options.pairingTtlMs ?? 10 * 60_000,
    });
  }

  async function persistPairingAndAuthenticate(payload) {
    if (payload?.device_id !== options.deviceId || typeof payload?.device_token !== 'string') {
      throw new Error('Invalid paired device credential');
    }

    const credential = {
      device_id: payload.device_id,
      public_identity: payload.public_identity ?? publicIdentity,
      device_token: payload.device_token,
      paired_at: payload.paired_at ?? new Date().toISOString(),
    };

    if (options.credentialPath) {
      await writeCredentialsAtomic(options.credentialPath, credential);
    }

    deviceToken = credential.device_token;
    state.pairing = null;
    emitAuthenticationProof();
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
      state.lastError = null;
      if (deviceToken) emitAuthenticationProof();
      else announcePairing();
    });

    socket.on('disconnect', () => {
      state.connected = false;
      state.authenticated = false;
      stopHeartbeat?.();
      stopHeartbeat = null;
    });

    socket.on('agent:pairing-announced', payload => {
      state.pairing = { ...payload, code: pairingCode };
      options.onPairingAnnounced?.(state.pairing);
    });

    socket.on('agent:paired', payload => {
      persistPairingAndAuthenticate(payload).catch(error => {
        state.lastError = error.message;
        options.onError?.(error);
      });
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

    const connectingSocket = socket;
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
        connectingSocket.off('connect', onConnect);
        connectingSocket.off('connect_error', onError);
      };

      connectingSocket.once('connect', onConnect);
      connectingSocket.once('connect_error', onError);
    });

    connectingSocket.connect();
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
