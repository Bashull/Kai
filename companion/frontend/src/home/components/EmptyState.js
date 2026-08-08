export default function EmptyState({ section }) {
  return (
    <div className="empty-state">
      <span aria-hidden="true">◇</span>
      <p>Nada listo en {section.toLowerCase()} todavía.</p>
    </div>
  );
}
