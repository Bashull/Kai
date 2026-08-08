export function groupBySection(items) {
  return items.reduce((acc, item) => {
    for (const section of item.sections || []) {
      (acc[section] ||= []).push(item);
    }
    return acc;
  }, {});
}

export function searchCatalog(items, query) {
  const q = query.trim().toLocaleLowerCase('es');
  if (!q) return items;
  return items.filter(item => [
    item.title,
    item.kind,
    item.description,
    ...(item.tags || []),
    ...(item.sections || []),
  ].join(' ').toLocaleLowerCase('es').includes(q));
}

export function primaryAction(item) {
  if (item.status === 'FUNCTIONAL' && item.launch_target) {
    return { label: 'USAR', target: item.launch_target, kind: item.launch_kind };
  }
  if (item.status === 'IN_DEVELOPMENT' && item.continue_target) {
    return { label: 'CONTINUAR', target: item.continue_target, kind: 'continue' };
  }
  return { label: 'ABRIR', target: item.launch_target || item.canonical_source || null, kind: item.launch_kind };
}
