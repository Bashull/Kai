import { useEffect, useState } from 'react';
import { groupBySection } from './catalogModel';
import HomeHeader from './components/HomeHeader';
import KaiPresence from './components/KaiPresence';
import CatalogSection from './components/CatalogSection';
import SearchPalette from './components/SearchPalette';
import QuickLook from './components/QuickLook';
import '../styles/tokens.css';
import '../styles/home.css';

const SECTION_ORDER = [
  'CONTINUAR',
  'APLICACIONES',
  'KAI',
  'MUNDOS Y PROYECTOS',
  'CREACIÓN VISUAL',
  'VÍDEO Y MÚSICA',
  'LABORATORIO',
];

export default function HomePage({ items = [], loading, error, onOpenSearch, onOpenQuickLook }) {
  const [searchOpen, setSearchOpen] = useState(false);
  const [quickLookItem, setQuickLookItem] = useState(null);
  const grouped = groupBySection(items);
  const visibleSections = SECTION_ORDER.filter(section =>
    section === 'CONTINUAR' || section === 'APLICACIONES' || (grouped[section]?.length)
  );

  useEffect(() => {
    const handler = event => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const openSearch = () => {
    setSearchOpen(true);
    onOpenSearch?.();
  };

  const openQuickLook = item => {
    setQuickLookItem(item);
    onOpenQuickLook?.(item);
  };

  const selectSearchResult = item => {
    setSearchOpen(false);
    setQuickLookItem(item);
  };

  return (
    <main className="home-shell">
      <HomeHeader onOpenSearch={openSearch} />
      <KaiPresence />
      {loading && <p className="home-notice">Cargando catálogo…</p>}
      {error && <p className="home-notice home-notice--error">{error.message || String(error)}</p>}
      {visibleSections.map(section => (
        <CatalogSection
          key={section}
          title={section}
          items={grouped[section] || []}
          onOpenQuickLook={openQuickLook}
        />
      ))}
      <SearchPalette
        open={searchOpen}
        items={items}
        onClose={() => setSearchOpen(false)}
        onSelect={selectSearchResult}
      />
      <QuickLook item={quickLookItem} onClose={() => setQuickLookItem(null)} />
    </main>
  );
}

export { SECTION_ORDER };
