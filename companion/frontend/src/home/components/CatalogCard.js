import { primaryAction } from '../catalogModel';
import { resolveLaunch } from '../launch';
import StatusBadge from './StatusBadge';

function safeBrowserHref(target) {
  if (typeof target !== 'string') return null;
  const value = target.trim();
  if (!value) return null;

  try {
    if (value.startsWith('/')) {
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

export default function CatalogCard({ item, onOpenQuickLook }) {
  const action = primaryAction(item);
  const launch = resolveLaunch(item);
  const candidate = action.kind === 'continue' ? action.target : launch.enabled ? launch.href : null;
  const href = safeBrowserHref(candidate);

  return (
    <article className="catalog-card">
      <div className="catalog-card__meta">
        <StatusBadge status={item.status} />
        <span>{item.kind}</span>
      </div>
      <h3>{item.title}</h3>
      <p>{item.description || 'Sin descripción todavía.'}</p>
      <div className="catalog-card__actions">
        <button type="button" onClick={() => onOpenQuickLook?.(item)}>
          Vista rápida
        </button>
        {href ? (
          <a href={href}>{action.label}</a>
        ) : (
          <button type="button" disabled title={launch.reason || 'Destino no disponible'}>
            {action.kind === 'continue' ? action.label : launch.label}
          </button>
        )}
      </div>
    </article>
  );
}
