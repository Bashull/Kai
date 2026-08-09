import { render, screen } from '@testing-library/react';
import QuickLook from './QuickLook';

test('quick look exposes state and both useful actions', () => {
  render(<QuickLook item={{
    id: 'x', title: 'X', status: 'IN_DEVELOPMENT', description: 'Current state',
    updated_at: '2026-08-08T00:00:00.000Z', launch_kind: 'web_app',
    launch_target: '/x', continue_target: 'https://github.com/Bashull/Kai', canonical_source: null
  }} onClose={() => {}} />);
  expect(screen.getByRole('dialog')).toBeInTheDocument();
  expect(screen.getByText(/en desarrollo/i)).toBeInTheDocument();
  expect(screen.getByRole('link', { name: /usar/i })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: /continuar desarrollo/i })).toBeInTheDocument();
});

test('quick look moves keyboard focus inside the modal', () => {
  render(<QuickLook item={{
    id: 'focus', title: 'Focus', status: 'MATURE_CONCEPT', description: '',
    updated_at: '2026-08-08T00:00:00.000Z', launch_kind: 'concept',
    launch_target: null, continue_target: null, canonical_source: null
  }} onClose={() => {}} />);
  expect(screen.getByRole('button', { name: /cerrar vista rápida/i })).toHaveFocus();
});

test('local app future shows the disabled Nervous Link explanation', () => {
  render(<QuickLook item={{
    id: 'local', title: 'Local', status: 'FUNCTIONAL', description: '',
    updated_at: '2026-08-08T00:00:00.000Z', launch_kind: 'local_app_future',
    launch_target: 'C:/unsafe.exe', continue_target: null, canonical_source: null
  }} onClose={() => {}} />);
  expect(screen.getByText('Requiere Kai Bridge/Nervous Link autorizado')).toBeInTheDocument();
  expect(screen.queryByRole('link', { name: /usar/i })).not.toBeInTheDocument();
});
