const BROWSER_KINDS = new Set(['web_app', 'repo', 'document', 'download']);

export function resolveLaunch(item) {
  if (item.launch_kind === 'local_app_future') {
    return {
      enabled: false,
      href: null,
      label: 'PRÓXIMAMENTE',
      reason: 'Requiere Kai Bridge/Nervous Link autorizado'
    };
  }
  const href = item.launch_target || item.canonical_source || null;
  return {
    enabled: Boolean(href && BROWSER_KINDS.has(item.launch_kind)),
    href,
    label: href ? 'ABRIR' : 'SIN DESTINO',
    reason: href ? null : 'No hay destino verificado todavía'
  };
}
