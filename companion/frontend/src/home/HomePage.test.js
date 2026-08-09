import { fireEvent, render, screen } from '@testing-library/react';
import HomePage from './HomePage';
import KaiPresence from './components/KaiPresence';

const items = [{
  id: 'kai', title: 'Kai', kind: 'project', sections: ['CONTINUAR', 'KAI'],
  status: 'IN_DEVELOPMENT', description: 'Mundo Kai', cover: null, tags: [],
  updated_at: '2026-08-08T00:00:00.000Z', canonical_source: null,
  launch_kind: 'concept', launch_target: null, continue_target: '/workspace'
}];

test('HOME prioritizes Continuar and Aplicaciones', () => {
  render(<HomePage items={items} loading={false} error={null} onOpenSearch={() => {}} onOpenQuickLook={() => {}} />);
  expect(screen.getByRole('heading', { name: /continuar/i })).toBeInTheDocument();
  expect(screen.getByRole('heading', { name: /aplicaciones/i })).toBeInTheDocument();
  expect(screen.getAllByText('Kai').length).toBeGreaterThan(0);
});

test('HOME never exposes a local continue path as a link', () => {
  const unsafe = [{ ...items[0], id: 'unsafe', sections: ['CONTINUAR'], continue_target: 'C:/unsafe.exe' }];
  render(<HomePage items={unsafe} loading={false} error={null} onOpenSearch={() => {}} onOpenQuickLook={() => {}} />);
  expect(screen.queryByRole('link', { name: 'CONTINUAR' })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'CONTINUAR' })).toBeDisabled();
});

test('Kai presence falls back to the neutral core when the private canon is unavailable', () => {
  render(<KaiPresence />);
  fireEvent.error(screen.getByRole('img', { name: 'Kai' }));
  expect(screen.getByLabelText('Kai')).toBeInTheDocument();
  expect(screen.queryByRole('img', { name: 'Kai' })).not.toBeInTheDocument();
});

test('HOME keeps primary section headings visible while loading', () => {
  render(<HomePage items={[]} loading error={null} onOpenSearch={() => {}} onOpenQuickLook={() => {}} />);
  expect(screen.getByRole('heading', { name: /continuar/i })).toBeInTheDocument();
  expect(screen.getByRole('heading', { name: /aplicaciones/i })).toBeInTheDocument();
});

test('HOME never exposes unsafe browser launch schemes', () => {
  const unsafe = [{ ...items[0], id: 'unsafe-web', sections: ['APLICACIONES'], status: 'FUNCTIONAL', launch_kind: 'web_app', launch_target: 'javascript:alert(1)', continue_target: null }];
  render(<HomePage items={unsafe} loading={false} error={null} onOpenSearch={() => {}} onOpenQuickLook={() => {}} />);
  expect(screen.queryByRole('link', { name: 'USAR' })).not.toBeInTheDocument();
});

test('section with spaces keeps an accessible region name', () => {
  const world = [{ ...items[0], id: 'world', title: 'World', sections: ['MUNDOS Y PROYECTOS'] }];
  render(<HomePage items={world} loading={false} error={null} onOpenSearch={() => {}} onOpenQuickLook={() => {}} />);
  expect(screen.getByRole('region', { name: 'MUNDOS Y PROYECTOS' })).toBeInTheDocument();
});

test('HOME rejects backslash paths that browsers normalize to another origin', () => {
  const bypass = [{ ...items[0], id: 'origin-bypass', sections: ['APLICACIONES'], status: 'FUNCTIONAL', launch_kind: 'web_app', launch_target: String.raw`/\evil.example/path`, continue_target: null }];
  render(<HomePage items={bypass} loading={false} error={null} onOpenSearch={() => {}} onOpenQuickLook={() => {}} />);
  expect(screen.queryByRole('link', { name: 'USAR' })).not.toBeInTheDocument();
});

test('Ctrl+K opens global search from HOME', () => {
  render(<HomePage items={items} loading={false} error={null} onOpenSearch={() => {}} onOpenQuickLook={() => {}} />);
  fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
  expect(screen.getByRole('dialog', { name: /buscar en kai home/i })).toBeInTheDocument();
});

test('card quick look opens the item dialog', () => {
  render(<HomePage items={items} loading={false} error={null} onOpenSearch={() => {}} onOpenQuickLook={() => {}} />);
  fireEvent.click(screen.getAllByRole('button', { name: /vista rápida/i })[0]);
  expect(screen.getByRole('dialog', { name: 'Kai' })).toBeInTheDocument();
});
