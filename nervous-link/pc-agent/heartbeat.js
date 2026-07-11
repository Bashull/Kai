'use strict';

function startHeartbeat({ intervalMs = 15000, send }) {
  if (typeof send !== 'function') {
    throw new Error('Heartbeat send callback is required');
  }

  const emit = () => send({
    action: 'heartbeat',
    timestamp: new Date().toISOString(),
    pid: process.pid,
  });

  const timer = setInterval(emit, intervalMs);
  timer.unref?.();
  return () => clearInterval(timer);
}

module.exports = { startHeartbeat };
