import { useEffect, useState } from 'react';
import { searchCatalog } from '../catalogModel';

export default function SearchPalette({ open, items, onClose, onSelect }) {
  const [query, setQuery] = useState('');
  const results = searchCatalog(items || [], query);
  const firstResult = results[0] || null;

  useEffect(() => {
    if (!open) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const handler = event => {
      if (event.key === 'Escape') onClose?.();
      if (event.key === 'Enter' && firstResult) {
        event.preventDefault();
        onSelect?.(firstResult);
      }
    };
    window.addEventListener('keydown', handler);
    return () => {
      window.removeEventListener('keydown', handler);
      document.body.style.overflow = previousOverflow;
    };
  }, [open, firstResult, onClose, onSelect]);

  if (!open) return null;

  return (
    <div className="home-overlay">
      <div className="search-palette" role="dialog" aria-modal="true" aria-label="Buscar en KAI HOME">
        <div className="search-palette__header">
          <input
            autoFocus
            type="search"
            role="searchbox"
            value={query}
            onChange={event => setQuery(event.target.value)}
            placeholder="Busca proyectos, mundos, herramientas…"
          />
          <button type="button" onClick={onClose} aria-label="Cerrar búsqueda">×</button>
        </div>
        <div className="search-palette__results">
          {results.map(item => (
            <button key={item.id} type="button" onClick={() => onSelect?.(item)}>
              <strong>{item.title}</strong>
              <span>{item.kind}</span>
            </button>
          ))}
          {!results.length && <p>Sin resultados.</p>}
        </div>
      </div>
    </div>
  );
}
