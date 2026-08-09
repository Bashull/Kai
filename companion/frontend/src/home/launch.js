const BROWSER_KINDS = new Set(['web_app', 'repo', 'document', 'download']);

export function safeBrowserHref(target) {
  if (typeof target !== 'string') return null;
  const value = target.trim();
  if (!value) return null;

  try {
    if (value.startsWith('/')) {
      if (value.startsWith('//') || value.includes('\\')) return null;
      const base = new URL('https://kai.home.invalid/');
      const resolved = new URL(value, base);
      return resolved.origin === base.origin ? value : null;
    }
    const resolved = new URL(value);
    return resolved.protocol === 'http:' || resolved.protocol === 'https:' ? value : null;
  } catch {
    return null;
  }
}

export function resolveLaunch(item) {
  if (item.launch_kind === 'local_app_future') {
    return {
      enabled: false,
      href: null,
      label: 'PRÓXIMAMENTE',
      reason: 'Requiere Kai Bridge/Nervous Link autorizado'
    };
  }
  const rawHref = item.launch_target || item.canonical_source || null;
  const href = safeBrowserHref(rawHref);
  return {
    enabled: Boolean(href && BROWSER_KINDS.has(item.launch_kind)),
    href,
    label: rawHref ? 'ABRIR' : 'SIN DESTINO',
    reason: href ? null : rawHref ? 'Destino no permitido' : 'No hay destino verificado todavía'
  };
}
