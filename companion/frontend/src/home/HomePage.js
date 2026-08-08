import { groupBySection } from './catalogModel';
import HomeHeader from './components/HomeHeader';
import KaiPresence from './components/KaiPresence';
import CatalogSection from './components/CatalogSection';
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
  const grouped = groupBySection(items);
  const visibleSections = SECTION_ORDER.filter(section =>
    section === 'CONTINUAR' || section === 'APLICACIONES' || (grouped[section]?.length)
  );

  return (
    <main className="home-shell">
      <HomeHeader onOpenSearch={onOpenSearch} />
      <KaiPresence />
      {loading && <p className="home-notice">Cargando catálogo…</p>}
      {error && <p className="home-notice home-notice--error">{error.message || String(error)}</p>}
      {!loading && visibleSections.map(section => (
        <CatalogSection
          key={section}
          title={section}
          items={grouped[section] || []}
          onOpenQuickLook={onOpenQuickLook}
        />
      ))}
    </main>
  );
}

export { SECTION_ORDER };
