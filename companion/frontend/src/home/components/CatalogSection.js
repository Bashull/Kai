import CatalogCard from './CatalogCard';
import EmptyState from './EmptyState';

export default function CatalogSection({ title, items, onOpenQuickLook }) {
  const sectionId = `section-${encodeURIComponent(title)}`;
  return (
    <section className="catalog-section" aria-labelledby={sectionId}>
      <div className="catalog-section__heading">
        <h2 id={sectionId}>{title}</h2>
        <span>{items.length}</span>
      </div>
      {items.length ? (
        <div className="catalog-grid">
          {items.map(item => (
            <CatalogCard key={`${title}-${item.id}`} item={item} onOpenQuickLook={onOpenQuickLook} />
          ))}
        </div>
      ) : (
        <EmptyState section={title} />
      )}
    </section>
  );
}
