import { useEffect } from 'react';
import { resolveLaunch, safeBrowserHref } from '../launch';
import StatusBadge from './StatusBadge';

function safeExternalHref(target) {
  const href = safeBrowserHref(target);
  return href && /^https?:\/\//i.test(href) ? href : null;
}

export default function QuickLook({ item, onClose }) {
  useEffect(() => {
    if (!item) return undefined;
    const handler = event => {
      if (event.key === 'Escape') onClose?.();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [item, onClose]);

  if (!item) return null;

  const launch = resolveLaunch(item);
  const continueHref = safeBrowserHref(item.continue_target);
  const sourceHref = safeExternalHref(item.canonical_source);
  const titleId = `quick-look-${encodeURIComponent(item.id)}`;

  return (
    <div className="home-overlay home-overlay--quick-look">
      <section className="quick-look" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <div className="quick-look__header">
          <div>
            <StatusBadge status={item.status} />
            <h2 id={titleId}>{item.title}</h2>
          </div>
          <button autoFocus type="button" onClick={onClose} aria-label="Cerrar vista rápida">×</button>
        </div>
        <p className="quick-look__description">{item.description || 'Sin descripción todavía.'}</p>
        {item.updated_at && <p className="quick-look__updated">Actualizado: {item.updated_at}</p>}
        {item.launch_kind === 'local_app_future' && (
          <p className="quick-look__notice">{launch.reason}</p>
        )}
        <div className="quick-look__actions">
          {launch.enabled && launch.href && <a href={launch.href}>USAR</a>}
          {item.continue_target && (continueHref ? (
            <a href={continueHref}>CONTINUAR DESARROLLO</a>
          ) : (
            <button type="button" disabled title="Destino no permitido">CONTINUAR DESARROLLO</button>
          ))}
          {sourceHref && <a href={sourceHref}>FUENTE CANÓNICA</a>}
        </div>
      </section>
    </div>
  );
}
