import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SearchPalette from './SearchPalette';

const items = [
  { id: 'waffles', title: 'Waffles', kind: 'character', description: '', tags: ['oni'], sections: ['KAI'] },
  { id: 'ea', title: 'Eternal Agony', kind: 'world', description: '', tags: ['vitae'], sections: ['MUNDOS Y PROYECTOS'] },
];

test('search filters without requiring category knowledge', async () => {
  const user = userEvent.setup();
  render(<SearchPalette open items={items} onClose={() => {}} onSelect={() => {}} />);
  await user.type(screen.getByRole('searchbox'), 'vitae');
  expect(screen.getByText('Eternal Agony')).toBeInTheDocument();
  expect(screen.queryByText('Waffles')).not.toBeInTheDocument();
});

test('Escape closes and restores body scrolling', async () => {
  const user = userEvent.setup();
  const onClose = jest.fn();
  document.body.style.overflow = 'auto';
  const { unmount } = render(<SearchPalette open items={items} onClose={onClose} onSelect={() => {}} />);
  expect(document.body.style.overflow).toBe('hidden');
  await user.keyboard('{Escape}');
  expect(onClose).toHaveBeenCalledTimes(1);
  unmount();
  expect(document.body.style.overflow).toBe('auto');
});

test('Enter opens the first visible result', async () => {
  const user = userEvent.setup();
  const onSelect = jest.fn();
  render(<SearchPalette open items={items} onClose={() => {}} onSelect={onSelect} />);
  await user.type(screen.getByRole('searchbox'), 'vitae');
  await user.keyboard('{Enter}');
  expect(onSelect).toHaveBeenCalledWith(items[1]);
});
