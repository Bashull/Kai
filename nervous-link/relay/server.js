'use strict';

const http = require('node:http');
const crypto = require('node:crypto');
const express = require('express');
const { Server } = require('socket.io');
const { SessionRegistry } = require('./sessionRegistry');
const { ReplayGuard } = require('./replayGuard');
const { verifyHmacProof } = require('./auth');
const { validateRequestEnvelope } = require('../protocol/envelope');

function safeTokenEqual(actual, expected) {
  const left = Buffer.from(String(actual ?? ''));
  const right = Buffer.from(String(expected ?? ''));
  return left.length === right.length && crypto.timingSafeEqual(left, right);
}

function createRelayServer(options = {}) {
  const app = express();
  app.use(express.json({ limit: '1mb' }));

  const httpServer = http.createServer(app);
  const io = new Server(httpServer, { cors: { origin: false } });
  const registry = options.registry ?? new SessionRegistry();
  const replayGuard = options.replayGuard ?? new ReplayGuard();
  const ownerToken = options.ownerToken ?? process.env.KAI_NERVOUS_LINK_OWNER_TOKEN;

  if (!ownerToken) {
    throw new Error('KAI_NERVOUS_LINK_OWNER_TOKEN is required');
  }

  const pairingSockets = new Map();
  const pendingClients = new Map();

  app.get('/health', (_req, res) => {
    res.json({ ok: true, protocol: 'kai-nervous-link/0.1' });
  });

  app.post('/pair/approve', (req, res) => {
    const authHeader = req.get('authorization');
    if (!safeTokenEqual(authHeader, `Bearer ${ownerToken}`)) {
      res.status(401).json({ error: 'UNAUTHORIZED' });
      return;
    }

    try {
      const approved = registry.approvePairing(req.body);
      const pairingSocket = pairingSockets.get(req.body.pairing_id);
      if (pairingSocket?.connected) {
        pairingSocket.emit('agent:paired', approved);
      }
      pairingSockets.delete(req.body.pairing_id);
      res.json(approved);
    } catch (error) {
      res.status(400).json({ error: error.message });
    }
  });

  io.on('connection', socket => {
    socket.on('agent:announce-pairing', payload => {
      try {
        const announced = registry.announcePairing(payload);
        pairingSockets.set(announced.pairing_id, socket);
        socket.emit('agent:pairing-announced', announced);
      } catch (error) {
        socket.emit('agent:error', { error: error.message });
      }
    });

    socket.on('agent:authenticate', payload => {
      const device = registry.getDevice(payload?.device_id);
      const proofPayload = payload?.proof_payload;
      const proofBindsSocket =
        proofPayload?.device_id === payload?.device_id &&
        proofPayload?.socket_id === socket.id;

      if (
        !device ||
        !proofBindsSocket ||
        !verifyHmacProof(device.device_token, proofPayload, payload?.proof)
      ) {
        socket.emit('agent:error', { error: 'AUTHENTICATION_FAILED' });
        return;
      }

      socket.data.device_id = payload.device_id;
      registry.registerAgentSocket(payload.device_id, socket);
      socket.emit('agent:authenticated', { device_id: payload.device_id });
    });

    socket.on('client:request', envelope => {
      try {
        const { owner_token: presentedOwnerToken, ...forwardEnvelope } = envelope ?? {};
        if (!safeTokenEqual(presentedOwnerToken, ownerToken)) {
          throw new Error('UNAUTHORIZED');
        }

        validateRequestEnvelope(forwardEnvelope);
        replayGuard.checkAndRemember(forwardEnvelope.nonce, Date.parse(forwardEnvelope.timestamp));

        const agent = registry.getAgentSocket(forwardEnvelope.device_id);
        if (!agent) {
          throw new Error('DEVICE_OFFLINE');
        }

        pendingClients.set(forwardEnvelope.request_id, socket);
        agent.emit('agent:request', forwardEnvelope);
      } catch (error) {
        socket.emit('client:response', {
          request_id: envelope?.request_id ?? null,
          status: 'error',
          error: error.message,
        });
      }
    });

    socket.on('agent:response', response => {
      const client = pendingClients.get(response?.request_id);
      if (!client) return;

      client.emit(`client:response:${response.request_id}`, response);
      client.emit('client:response', response);
      pendingClients.delete(response.request_id);
    });

    socket.on('disconnect', () => {
      if (socket.data.device_id) {
        registry.removeAgentSocket(socket.data.device_id, socket.id);
      }

      for (const [requestId, client] of pendingClients) {
        if (client.id === socket.id) {
          pendingClients.delete(requestId);
        }
      }

      for (const [pairingId, pairingSocket] of pairingSockets) {
        if (pairingSocket.id === socket.id) {
          pairingSockets.delete(pairingId);
        }
      }
    });
  });

  return {
    app,
    httpServer,
    io,
    registry,
    start(port = 0, host = '127.0.0.1') {
      return new Promise((resolve, reject) => {
        httpServer.once('error', reject);
        httpServer.listen(port, host, () => {
          httpServer.off('error', reject);
          resolve(httpServer.address());
        });
      });
    },
    stop() {
      return new Promise(resolve => {
        io.close(() => {
          if (!httpServer.listening) {
            resolve();
            return;
          }
          httpServer.close(resolve);
        });
      });
    },
  };
}

module.exports = { createRelayServer, safeTokenEqual };
