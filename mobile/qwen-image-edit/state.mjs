export function createSession({ profile, prompt, files, steps = 10 }) {
  return {
    version: 2,
    id: `local-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`,
    profile: (profile || 'default').trim(),
    prompt: (prompt || '').trim(),
    steps: Number(steps) || 10,
    cursor: 0,
    serverRunId: null,
    createdAt: new Date().toISOString(),
    items: (files || []).map((file, index) => ({
      index,
      key: file.key,
      name: file.name || file.key,
      status: 'pending',
      attempts: [],
      choice: null,
      promote: false,
    })),
  };
}

export function currentItem(session) {
  if (!session || session.cursor >= session.items.length) return null;
  return session.items[session.cursor];
}

export function recordAttempt(session, index, attempt) {
  const item = session.items[index];
  if (!item) throw new Error(`Unknown item index ${index}`);
  item.attempts.push({ ...attempt, number: item.attempts.length + 1 });
  item.status = 'review';
  return item;
}

function advance(session, after) {
  let next = session.items.length;
  for (let i = after + 1; i < session.items.length; i += 1) {
    if (!['done', 'skipped'].includes(session.items[i].status)) {
      next = i;
      break;
    }
  }
  session.cursor = next;
}

export function chooseCandidate(session, index, choice, promote = false) {
  const item = session.items[index];
  if (!item) throw new Error(`Unknown item index ${index}`);
  const normalized = String(choice || '').toUpperCase();
  if (!['A', 'B'].includes(normalized)) throw new Error('choice must be A or B');
  if (!item.attempts.length) throw new Error('No candidates to choose from');
  item.choice = normalized;
  item.promote = Boolean(promote);
  item.status = 'done';
  item.decidedAt = new Date().toISOString();
  advance(session, index);
  return item;
}

export function skipItem(session, index) {
  const item = session.items[index];
  if (!item) throw new Error(`Unknown item index ${index}`);
  item.status = 'skipped';
  item.skippedAt = new Date().toISOString();
  advance(session, index);
  return item;
}
