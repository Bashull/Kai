import { useState } from 'react';

export default function KaiPresence() {
  const [failed, setFailed] = useState(false);

  return (
    <aside className="kai-presence">
      {!failed ? (
        <img
          className="kai-presence__image"
          src="/api/private-assets/kai-canon"
          alt="Kai"
          onError={() => setFailed(true)}
        />
      ) : (
        <div className="kai-presence__fallback" aria-label="Kai">
          <span className="kai-core" aria-hidden="true" />
          <span>KAI</span>
        </div>
      )}
    </aside>
  );
}
