#!/data/data/com.termux/files/usr/bin/node
'use strict';

const fs = require('fs');
const path = require('path');
const http = require('http');
const crypto = require('crypto');
const { WebSocketServer, WebSocket } = require('ws');

const HOME = process.env.HOME || '/data/data/com.termux/files/home';
const ROOT = path.join(HOME, '.kai_mobile', 'bedrock-ws');
const STATE_DIR = path.join(ROOT, 'state');
const TOKEN_FILE = path.join(ROOT, 'bridge-token');
const STATUS_FILE = path.join(STATE_DIR, 'status.json');
const EVENTS_FILE = path.join(STATE_DIR, 'events.jsonl');
const WS_PORT = Number(process.env.KAI_BEDROCK_WS_PORT || 6464);
const HTTP_PORT = Number(process.env.KAI_BEDROCK_HTTP_PORT || 6465);
const HOST = '127.0.0.1';

fs.mkdirSync(STATE_DIR, { recursive: true });
let token;
if (fs.existsSync(TOKEN_FILE)) token = fs.readFileSync(TOKEN_FILE, 'utf8').trim();
else {
  token = crypto.randomBytes(32).toString('base64url');
  fs.writeFileSync(TOKEN_FILE, token, { mode: 0o600 });
}

const subscriptions = [
  'PlayerTravelled','PlayerTeleported','PlayerTransform','PlayerMessage',
  'BlockPlaced','BlockBroken','ItemAcquired','ItemCrafted','ItemDropped',
  'ItemEquipped','ItemInteracted','MobInteracted','MobEffectChanged',
  'BossKilled','PetDied','SlashCommandExecuted','PlayerGameModeSet',
  'GameRulesUpdated','WorldGenerated','StartWorld','ScreenChanged'
];

const state = {
  ok: true,
  startedAt: Date.now(),
  wsPort: WS_PORT,
  httpPort: HTTP_PORT,
  clients: 0,
  connected: false,
  lastMessageAt: null,
  lastEvent: null,
  latest: {},
  pendingCommands: 0,
  subscriptions,
  transport: 'minecraft-bedrock-wsserver',
  actionPolicy: 'sensor-first; no world-changing commands exposed'
};
const sockets = new Set();
const pending = new Map();

function atomicJson(file, value) {
  const tmp = file + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(value, null, 2));
  fs.renameSync(tmp, file);
}
function saveStatus() {
  state.uptimeS = Math.round((Date.now() - state.startedAt)/100)/10;
  state.pendingCommands = pending.size;
  atomicJson(STATUS_FILE, state);
}
function appendEvent(obj) {
  fs.appendFileSync(EVENTS_FILE, JSON.stringify(obj) + '\n');
}
function packet(purpose, body) {
  return {
    header: {
      version: 1,
      requestId: crypto.randomUUID(),
      messageType: 'commandRequest',
      messagePurpose: purpose
    },
    body
  };
}
function subscribe(ws, name) {
  ws.send(JSON.stringify(packet('subscribe', { eventName: name })));
}
function safeCommandAllowed(cmd) {
  const s = cmd.trim().replace(/^\//,'');
  return /^scriptevent\s+kai:[a-z0-9_.:-]+(?:\s|$)/i.test(s)
      || /^testfor\b/i.test(s)
      || /^list\b/i.test(s);
}
function sendCommand(ws, commandLine) {
  if (!safeCommandAllowed(commandLine)) throw new Error('command_not_allowed_by_survival_policy');
  const p = packet('commandRequest', {
    version: 1,
    origin: { type: 'player' },
    commandLine: commandLine.replace(/^\//,'')
  });
  pending.set(p.header.requestId, { ts: Date.now(), commandLine });
  ws.send(JSON.stringify(p));
  return p.header.requestId;
}

const wss = new WebSocketServer({ host: HOST, port: WS_PORT });
wss.on('connection', (ws, req) => {
  sockets.add(ws);
  state.clients = sockets.size;
  state.connected = true;
  state.lastConnectAt = Date.now();
  state.peer = req.socket.remoteAddress;
  saveStatus();

  for (const e of subscriptions) {
    try { subscribe(ws, e); } catch (_) {}
  }

  ws.on('message', data => {
    let msg;
    try { msg = JSON.parse(data.toString()); } catch (e) {
      appendEvent({ts:Date.now(), kind:'invalid_json', sample:data.toString().slice(0,240)});
      return;
    }
    const h = msg.header || {};
    state.lastMessageAt = Date.now();

    if (h.messagePurpose === 'event') {
      const name = h.eventName || 'UnknownEvent';
      const ev = { ts: Date.now(), kind:'event', name, body: msg.body || {} };
      state.latest[name] = ev;
      state.lastEvent = ev;
      appendEvent(ev);
    } else if (h.messagePurpose === 'commandResponse') {
      const id = h.requestId;
      const q = pending.get(id);
      const ev = { ts:Date.now(), kind:'commandResponse', requestId:id, request:q||null, body:msg.body||{} };
      if (id) pending.delete(id);
      state.lastCommandResponse = ev;
      appendEvent(ev);
    } else {
      appendEvent({ ts:Date.now(), kind:'packet', header:h, body:msg.body||{} });
    }
    saveStatus();
  });
  ws.on('close', () => {
    sockets.delete(ws);
    state.clients = sockets.size;
    state.connected = sockets.size > 0;
    state.lastDisconnectAt = Date.now();
    saveStatus();
  });
  ws.on('error', err => {
    state.lastWsError = String(err && err.message || err);
    saveStatus();
  });
});
wss.on('listening', saveStatus);
wss.on('error', err => { state.ok=false; state.lastWsError=String(err.message||err); saveStatus(); });

function auth(req) {
  const h = req.headers.authorization || '';
  return h === 'Bearer ' + token;
}
function json(res, code, obj) {
  const b = Buffer.from(JSON.stringify(obj));
  res.writeHead(code, {'content-type':'application/json','content-length':b.length});
  res.end(b);
}
const api = http.createServer((req,res) => {
  if (!auth(req)) return json(res,401,{ok:false,error:'unauthorized'});
  if (req.method === 'GET' && req.url === '/status') return json(res,200,state);
  if (req.method === 'GET' && req.url === '/health') return json(res,200,{ok:true,connected:state.connected,clients:state.clients});
  if (req.method === 'POST' && req.url === '/command') {
    let body='';
    req.on('data', c => { if (body.length < 8192) body += c; });
    req.on('end', () => {
      try {
        const j=JSON.parse(body||'{}');
        if (typeof j.command !== 'string') throw new Error('command_required');
        const ws=[...sockets].find(s=>s.readyState===WebSocket.OPEN);
        if (!ws) throw new Error('minecraft_not_connected');
        const requestId=sendCommand(ws,j.command);
        json(res,202,{ok:true,requestId});
      } catch(e) { json(res,400,{ok:false,error:String(e.message||e)}); }
    });
    return;
  }
  json(res,404,{ok:false,error:'not_found'});
});
api.listen(HTTP_PORT, HOST, saveStatus);

setInterval(() => {
  const now=Date.now();
  for (const [id,q] of pending) if (now-q.ts > 10000) pending.delete(id);
  saveStatus();
},1000);

function shutdown() {
  try { api.close(); } catch (_) {}
  try { wss.close(); } catch (_) {}
  process.exit(0);
}
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
