export default function HomeHeader({ onOpenSearch }) {
  return (
    <header className="home-header">
      <div>
        <p className="home-header__eyebrow">KAI HOME</p>
        <h1>Todo lo que sigue vivo, a mano.</h1>
      </div>
      <button className="home-header__search" type="button" onClick={onOpenSearch}>
        Buscar
        <span aria-hidden="true">Ctrl K</span>
      </button>
    </header>
  );
}
