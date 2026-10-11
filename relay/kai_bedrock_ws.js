#!/data/data/com.termux/files/usr/bin/node
'use strict'

const fs = require('fs')
const http = require('http')
const path = require('path')
const crypto = require('crypto')
const { WebSocketServer } = require('ws')

const HOME = process.env.HOME || '/data/data/com.termux/files/home'
const BASE = path.join(HOME, '.kai_mobile')
const OUT = path.join(BASE, 'bedrock-ws')
const TOKEN = fs.readFileSync(path.join(BASE, 'kai-live-token'), 'utf8').trim()
const WS_HOST = process.env.KAI_BEDROCK_WS_HOST || '127.0.0.1'
const WS_PORT = Number(process.env.KAI_BEDROCK_WS_PORT || 19137)
const HTTP_HOST = process.env.KAI_BEDROCK_HTTP_HOST || '127.0.0.1'
const HTTP_PORT = Number(process.env.KAI_BEDROCK_HTTP_PORT || 7192)
const STATUS_FILE = path.join(OUT, 'status.json')
const EVENTS_FILE = path.join(OUT, 'events.jsonl')
const MAX_EVENTS = 256

fs.mkdirSync(OUT, { recursive: true })

const EVENT_NAMES = [
  'ApiInit','StartWorld','WorldLoaded','WorldUnloaded','GameSessionStart','GameSessionComplete',
  'PlayerJoin','PlayerLeave','PlayerTransform','PlayerTravelled','PlayerTeleported','PlayerDied',
  'EntitySpawned','MobKilled','MobInteracted','BlockBroken','BlockPlaced',
  'ItemAcquired','ItemCrafted','ItemDestroyed','ItemDropped','ItemUsed',
  'ScreenChanged','FocusGained','FocusLost','PerformanceMetrics','EndOfDay'
]

const state = {
  ok: true,
  started_at: Date.now(),
  websocket: { host: WS_HOST, port: WS_PORT, connected: false, connected_at: null, peer: null },
  http: { host: HTTP_HOST, port: HTTP_PORT },
  world: { loaded: false, session: null },
  player: { name: null, position: null, yRot: null, dimension: null, alive: null, last_transform_at: null },
  last_event: null,
  event_count: 0,
  recent_events: [],
  subscriptions: {},
  pending_commands: 0,
  last_error: null
}

let activeSocket = null
const pending = new Map()

function atomicWriteJson(file, value) {
  const tmp = file + '.tmp'
  fs.writeFileSync(tmp, JSON.stringify(value, null, 2))
  fs.renameSync(tmp, file)
}

function persist() {
  state.uptime_s = Math.round((Date.now() - state.started_at) / 100) / 10
  state.pending_commands = pending.size
  atomicWriteJson(STATUS_FILE, state)
}

function appendEvent(obj) {
  const row = JSON.stringify(obj)
  fs.appendFileSync(EVENTS_FILE, row + '\n')
  state.recent_events.push(obj)
  if (state.recent_events.length > MAX_EVENTS) state.recent_events.splice(0, state.recent_events.length - MAX_EVENTS)
  state.last_event = obj
  state.event_count += 1
}

function msgHeader(purpose, requestId = crypto.randomUUID()) {
  return { version: 1, requestId, messageType: 'commandRequest', messagePurpose: purpose }
}

function sendJson(ws, obj) {
  if (!ws || ws.readyState !== ws.OPEN) return false
  ws.send(JSON.stringify(obj))
  return true
}

function subscribe(ws, eventName) {
  const requestId = crypto.randomUUID()
  const payload = { header: msgHeader('subscribe', requestId), body: { eventName } }
  state.subscriptions[eventName] = { requestId, requested_at: Date.now(), acknowledged: false }
  sendJson(ws, payload)
}

function command(ws, commandLine, timeoutMs = 2500) {
  return new Promise((resolve, reject) => {
    if (!ws || ws.readyState !== ws.OPEN) return reject(new Error('minecraft websocket not connected'))
    const requestId = crypto.randomUUID()
    const timer = setTimeout(() => {
      pending.delete(requestId)
      reject(new Error('command timeout'))
      persist()
    }, timeoutMs)
    pending.set(requestId, { resolve, reject, timer, commandLine, sent_at: Date.now() })
    sendJson(ws, {
      header: msgHeader('commandRequest', requestId),
      body: { version: 1, commandLine, origin: { type: 'player' } }
    })
    persist()
  })
}

function extractPlayer(body) {
  if (!body || typeof body !== 'object') return null
  return body.player || body.sender || body.source || null
}

function updateFromEvent(name, body) {
  const p = extractPlayer(body)
  if (p && typeof p === 'object') {
    if (p.name != null) state.player.name = p.name
    if (p.position != null) state.player.position = p.position
    if (p.yRot != null) state.player.yRot = p.yRot
    if (p.dimension != null) state.player.dimension = p.dimension
    state.player.last_transform_at = Date.now()
  }
  if (name === 'PlayerDied') {
    state.player.alive = false
    state.player.last_death = { at: Date.now(), body }
  }
  if (name === 'PlayerJoin' || name === 'PlayerTransform' || name === 'PlayerTravelled' || name === 'PlayerTeleported') {
    state.player.alive = true
  }
  if (name === 'WorldLoaded' || name === 'StartWorld' || name === 'GameSessionStart') state.world.loaded = true
  if (name === 'WorldUnloaded' || name === 'GameSessionComplete') state.world.loaded = false
}

function handleMessage(ws, raw) {
  let msg
  try { msg = JSON.parse(raw.toString()) } catch (e) {
    state.last_error = { at: Date.now(), where: 'json', message: String(e) }
    persist()
    return
  }

  const h = msg.header || {}
  const purpose = h.messagePurpose || ''
  const requestId = h.requestId
  const eventName = h.eventName || (msg.body && msg.body.eventName)

  if (requestId && pending.has(requestId) && (purpose === 'commandResponse' || msg.body)) {
    const p = pending.get(requestId)
    clearTimeout(p.timer)
    pending.delete(requestId)
    p.resolve(msg)
  }

  if (purpose === 'commandResponse' && requestId) {
    for (const [name, sub] of Object.entries(state.subscriptions)) {
      if (sub.requestId === requestId) sub.acknowledged = true
    }
  }

  if (purpose === 'event' || eventName) {
    const name = eventName || 'unknown'
    const evt = { at: Date.now(), name, body: msg.body || {}, header: h }
    updateFromEvent(name, evt.body)
    appendEvent(evt)
  }
  persist()
}

const wss = new WebSocketServer({ host: WS_HOST, port: WS_PORT })
wss.on('connection', (ws, req) => {
  if (activeSocket && activeSocket !== ws) {
    try { activeSocket.close(1012, 'replaced by new Minecraft connection') } catch {}
  }
  activeSocket = ws
  state.websocket.connected = true
  state.websocket.connected_at = Date.now()
  state.websocket.peer = req.socket.remoteAddress || null
  state.last_error = null
  appendEvent({ at: Date.now(), name: '_ws_connected', body: { peer: state.websocket.peer } })
  for (const name of EVENT_NAMES) subscribe(ws, name)
  persist()

  ws.on('message', raw => handleMessage(ws, raw))
  ws.on('close', (code, reason) => {
    if (activeSocket === ws) activeSocket = null
    state.websocket.connected = false
    appendEvent({ at: Date.now(), name: '_ws_closed', body: { code, reason: reason.toString() } })
    persist()
  })
  ws.on('error', err => {
    state.last_error = { at: Date.now(), where: 'websocket', message: String(err) }
    persist()
  })
})

wss.on('listening', persist)
wss.on('error', err => {
  state.ok = false
  state.last_error = { at: Date.now(), where: 'wss', message: String(err) }
  persist()
})

function auth(req) {
  const h = req.headers.authorization || ''
  const q = new URL(req.url, 'http://localhost').searchParams.get('token') || ''
  const candidate = h.startsWith('Bearer ') ? h.slice(7) : q
  try {
    return candidate.length === TOKEN.length && crypto.timingSafeEqual(Buffer.from(candidate), Buffer.from(TOKEN))
  } catch { return false }
}

function json(res, code, obj) {
  const body = Buffer.from(JSON.stringify(obj))
  res.writeHead(code, { 'Content-Type': 'application/json', 'Content-Length': body.length })
  res.end(body)
}

const READ_ONLY_PREFIXES = [
  'querytarget ', 'testfor ', 'testforblock ', 'testforblocks ', 'list', 'help'
]

const api = http.createServer(async (req, res) => {
  if (!auth(req)) return json(res, 401, { ok: false, error: 'unauthorized' })
  const u = new URL(req.url, 'http://localhost')
  if (req.method === 'GET' && u.pathname === '/status') return json(res, 200, state)
  if (req.method === 'GET' && u.pathname === '/events') {
    const n = Math.max(1, Math.min(256, Number(u.searchParams.get('n') || 32)))
    return json(res, 200, { ok: true, events: state.recent_events.slice(-n) })
  }
  if (req.method === 'POST' && u.pathname === '/query') {
    let raw = ''
    for await (const chunk of req) {
      raw += chunk
      if (raw.length > 65536) return json(res, 413, { ok: false, error: 'body too large' })
    }
    let body
    try { body = JSON.parse(raw || '{}') } catch { return json(res, 400, { ok: false, error: 'invalid json' }) }
    const line = String(body.command || '').trim()
    const lower = line.toLowerCase()
    if (!READ_ONLY_PREFIXES.some(p => lower === p || lower.startsWith(p))) {
      return json(res, 403, { ok: false, error: 'read-only query allowlist' })
    }
    try {
      const reply = await command(activeSocket, line)
      return json(res, 200, { ok: true, command: line, reply })
    } catch (e) {
      return json(res, 503, { ok: false, error: String(e) })
    }
  }
  return json(res, 404, { ok: false, error: 'not found' })
})

api.listen(HTTP_PORT, HTTP_HOST, persist)

process.on('SIGTERM', () => { try { wss.close() } catch {}; try { api.close() } catch {}; process.exit(0) })
process.on('SIGINT', () => process.kill(process.pid, 'SIGTERM'))

setInterval(persist, 1000).unref()
persist()
