'use strict';

const fs = require('fs');
const http = require('http');
const path = require('path');
const crypto = require('crypto');
const { WebSocketServer, WebSocket } = require('ws');

const HOME = process.env.HOME || '/data/data/com.termux/files/home';
const BASE = path.join(HOME, '.kai_mobile');
const DIR = path.join(BASE, 'mcwss');
const TOKEN = fs.readFileSync(path.join(BASE, 'kai-live-token'), 'utf8').trim();

const WS_HOST = process.env.KAI_MCWSS_HOST || '127.0.0.1';
const WS_PORT = Number(process.env.KAI_MCWSS_PORT || 6464);
const API_HOST = process.env.KAI_MCWSS_API_HOST || '127.0.0.1';
const API_PORT = Number(process.env.KAI_MCWSS_API_PORT || 7192);
const MAX_EVENTS = 300;

fs.mkdirSync(DIR, { recursive: true });
const STATUS_PATH = path.join(DIR, 'status.json');
const EVENT_PATH = path.join(DIR, 'events.jsonl');

let minecraft = null;
let connectedAt = null;
let rxCount = 0;
let txCount = 0;
let events = [];
let latestTelemetry = null;
let latestKaiEvent = null;
let latestRaw = null;
let lastError = null;
let subscriptions = new Set();
const pending = new Map();

function uuid() {
  return crypto.randomUUID();
}

function atomicWriteJson(file, obj) {
  const tmp = file + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(obj, null, 2));
  fs.renameSync(tmp, file);
}

function appendEvent(e) {
  events.push(e);
  if (events.length > MAX_EVENTS) events = events.slice(-MAX_EVENTS);
  fs.appendFileSync(EVENT_PATH, JSON.stringify(e) + '\n');
}

function publicStatus() {
  return {
    ok: true,
    ws: {
      host: WS_HOST,
      port: WS_PORT,
      connected: !!(minecraft && minecraft.readyState === WebSocket.OPEN),
      connectedAt,
      rxCount,
      txCount,
      subscriptions: Array.from(subscriptions),
      lastError,
    },
    api: { host: API_HOST, port: API_PORT },
    latestTelemetry,
    latestKaiEvent,
    latestRaw,
    updatedAt: new Date().toISOString(),
  };
}

function persist() {
  try { atomicWriteJson(STATUS_PATH, publicStatus()); } catch (_) {}
}

function sendFrame(frame) {
  if (!minecraft || minecraft.readyState !== WebSocket.OPEN) {
    throw new Error('minecraft_not_connected');
  }
  minecraft.send(JSON.stringify(frame));
  txCount++;
  persist();
}

function subscribe(eventName) {
  const requestId = uuid();
  sendFrame({
    header: {
      version: 1,
      requestId,
      messageType: 'commandRequest',
      messagePurpose: 'subscribe',
    },
    body: { eventName },
  });
  subscriptions.add(eventName);
  return requestId;
}

function command(commandLine, timeoutMs = 2500) {
  const requestId = uuid();
  const frame = {
    header: {
      version: 1,
      requestId,
      messageType: 'commandRequest',
      messagePurpose: 'commandRequest',
    },
    body: {
      version: 1,
      commandLine,
      origin: { type: 'player' },
    },
  };
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(requestId);
      reject(new Error('command_timeout'));
    }, timeoutMs);
    pending.set(requestId, { resolve, reject, timer, commandLine });
    try { sendFrame(frame); } catch (e) {
      clearTimeout(timer);
      pending.delete(requestId);
      reject(e);
    }
  });
}

function maybeParseKai(obj) {
  const h = obj && obj.header || {};
  const b = obj && obj.body || {};
  const eventName = h.eventName || b.eventName || (b.properties && b.properties.EventName);
  let id = b.id || b.messageId || (b.properties && (b.properties.MessageId || b.properties.EventName));
  let message = b.message || (b.properties && (b.properties.Message || b.properties.message));

  if (eventName === 'ScriptEventReceived') {
    if (b.properties) {
      id = id || b.properties.Id || b.properties.id;
      message = message || b.properties.Message || b.properties.message;
    }
  }

  if (typeof message === 'string' && (String(id || '').startsWith('kai:') || message.includes('"schema":"kai.'))) {
    let parsed = null;
    try { parsed = JSON.parse(message); } catch (_) {}
    if (String(id || '').includes('telemetry') || (parsed && String(parsed.schema || '').startsWith('kai.eyes'))) {
      latestTelemetry = parsed || { id, message };
    } else {
      latestKaiEvent = parsed || { id, message };
    }
  }
}

const EVENT_NAMES = [
  'PlayerMessage',
  'PlayerDied',
  'PlayerTransform',
  'PlayerTravelled',
  'MobKilled',
  'BlockBroken',
  'BlockPlaced',
  'ItemUsed',
  'EntitySpawned',
  'ScriptEventReceived',
];

const wss = new WebSocketServer({ host: WS_HOST, port: WS_PORT });

wss.on('connection', (socket, req) => {
  if (minecraft && minecraft.readyState === WebSocket.OPEN) {
    try { minecraft.close(1000, 'replaced_by_new_minecraft_connection'); } catch (_) {}
  }
  minecraft = socket;
  connectedAt = new Date().toISOString();
  subscriptions.clear();
  lastError = null;
  appendEvent({ ts: Date.now(), type: 'mcwss_connected', from: req.socket.remoteAddress });
  persist();

  socket.on('message', (buf) => {
    rxCount++;
    let obj;
    try { obj = JSON.parse(buf.toString('utf8')); }
    catch (e) {
      lastError = 'invalid_json:' + e.message;
      appendEvent({ ts: Date.now(), type: 'raw_text', text: buf.toString('utf8').slice(0, 2000) });
      persist();
      return;
    }

    latestRaw = obj;
    maybeParseKai(obj);

    const requestId = obj && obj.header && obj.header.requestId;
    if (requestId && pending.has(requestId)) {
      const p = pending.get(requestId);
      pending.delete(requestId);
      clearTimeout(p.timer);
      p.resolve(obj);
    }

    const compact = { ts: Date.now(), type: 'minecraft_frame', frame: obj };
    appendEvent(compact);
    persist();
  });

  socket.on('close', (code, reason) => {
    appendEvent({ ts: Date.now(), type: 'mcwss_closed', code, reason: reason.toString() });
    if (minecraft === socket) minecraft = null;
    subscriptions.clear();
    persist();
  });

  socket.on('error', (err) => {
    lastError = 'websocket:' + err.message;
    appendEvent({ ts: Date.now(), type: 'mcwss_error', error: err.message });
    persist();
  });

  setTimeout(() => {
    if (socket !== minecraft || socket.readyState !== WebSocket.OPEN) return;
    for (const name of EVENT_NAMES) {
      try { subscribe(name); } catch (e) { lastError = e.message; }
    }
    persist();
  }, 150);
});

function authorized(req) {
  const auth = req.headers.authorization || '';
  return auth === 'Bearer ' + TOKEN;
}

function jsonResponse(res, code, obj) {
  const body = Buffer.from(JSON.stringify(obj, null, 2));
  res.writeHead(code, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': body.length,
    'Cache-Control': 'no-store',
  });
  res.end(body);
}

function readBody(req, limit = 65536) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let n = 0;
    req.on('data', c => {
      n += c.length;
      if (n > limit) { reject(new Error('body_too_large')); req.destroy(); return; }
      chunks.push(c);
    });
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

const api = http.createServer(async (req, res) => {
  if (!authorized(req)) return jsonResponse(res, 401, { ok: false, error: 'unauthorized' });
  const u = new URL(req.url, 'http://localhost');

  if (req.method === 'GET' && u.pathname === '/status') return jsonResponse(res, 200, publicStatus());
  if (req.method === 'GET' && u.pathname === '/telemetry') return jsonResponse(res, 200, { ok: true, telemetry: latestTelemetry, event: latestKaiEvent });
  if (req.method === 'GET' && u.pathname === '/events') {
    const n = Math.max(1, Math.min(100, Number(u.searchParams.get('limit') || 20)));
    return jsonResponse(res, 200, { ok: true, events: events.slice(-n) });
  }

  if (req.method === 'POST' && u.pathname === '/command') {
    try {
      const body = JSON.parse((await readBody(req)).toString('utf8') || '{}');
      const cmd = String(body.command || '').trim();
      const allowed =
        /^querytarget\b/i.test(cmd) ||
        /^list\b/i.test(cmd) ||
        /^testfor\b/i.test(cmd) ||
        /^scriptevent\s+kai:/i.test(cmd);
      if (!allowed) return jsonResponse(res, 403, { ok: false, error: 'command_not_allowlisted' });
      const response = await command(cmd, Number(body.timeout_ms || 2500));
      return jsonResponse(res, 200, { ok: true, command: cmd, response });
    } catch (e) {
      return jsonResponse(res, 500, { ok: false, error: e.message });
    }
  }

  return jsonResponse(res, 404, { ok: false, error: 'not_found' });
});

api.listen(API_PORT, API_HOST, () => persist());

process.on('SIGTERM', () => {
  try { api.close(); } catch (_) {}
  try { wss.close(); } catch (_) {}
  process.exit(0);
});
process.on('uncaughtException', e => {
  lastError = 'uncaught:' + e.message;
  appendEvent({ ts: Date.now(), type: 'uncaught', error: e.stack || e.message });
  persist();
});
process.on('unhandledRejection', e => {
  lastError = 'unhandled:' + String(e);
  appendEvent({ ts: Date.now(), type: 'unhandled', error: String(e) });
  persist();
});

persist();
