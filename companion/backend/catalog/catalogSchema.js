const STATUSES = ['FUNCTIONAL', 'IN_DEVELOPMENT', 'MATURE_CONCEPT'];
const LAUNCH_KINDS = ['web_app', 'repo', 'document', 'download', 'concept', 'local_app_future'];

function requireString(value, field) {
  if (typeof value !== 'string' || !value.trim()) throw new Error(`Invalid ${field}`);
  return value.trim();
}

function nullableString(value) {
  return value == null || value === '' ? null : String(value);
}

function stringArray(value, field) {
  if (!Array.isArray(value) || value.some(v => typeof v !== 'string')) {
    throw new Error(`Invalid ${field}`);
  }
  return [...new Set(value.map(v => v.trim()).filter(Boolean))];
}

function validateCatalogItem(input) {
  const status = requireString(input.status, 'status');
  const launchKind = requireString(input.launch_kind, 'launch_kind');
  if (!STATUSES.includes(status)) throw new Error(`Invalid status: ${status}`);
  if (!LAUNCH_KINDS.includes(launchKind)) throw new Error(`Invalid launch_kind: ${launchKind}`);

  return {
    id: requireString(input.id, 'id'),
    title: requireString(input.title, 'title'),
    kind: requireString(input.kind, 'kind'),
    sections: stringArray(input.sections, 'sections'),
    status,
    description: String(input.description || ''),
    cover: nullableString(input.cover),
    tags: stringArray(input.tags || [], 'tags'),
    updated_at: requireString(input.updated_at, 'updated_at'),
    canonical_source: nullableString(input.canonical_source),
    launch_kind: launchKind,
    launch_target: nullableString(input.launch_target),
    continue_target: nullableString(input.continue_target),
  };
}

module.exports = { STATUSES, LAUNCH_KINDS, validateCatalogItem };
