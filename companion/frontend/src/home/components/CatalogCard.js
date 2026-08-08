import { primaryAction } from '../catalogModel';
import { resolveLaunch } from '../launch';
import StatusBadge from './StatusBadge';

function safeContinueHref(target) {
  if (typeof target !== 'string') return null;
  if (target.startsWith('/')) return target;
  if (/^https?:\/\//i.test(target)) return target;
  return null;
}

export default function CatalogCard({ item, onOpenQuickLook }) {
  const action = primaryAction(item);
  const launch = resolveLaunch(item);
  const href = action.kind === 'continue'
    ? safeContinueHref(action.target)
    : launch.enabled ? launch.href : null;

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
