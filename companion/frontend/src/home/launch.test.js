import { resolveLaunch } from './launch';

test('local app is never launched by browser in v0.1', () => {
  expect(resolveLaunch({ launch_kind: 'local_app_future', launch_target: 'C:/unsafe.exe' })).toEqual({
    enabled: false,
    href: null,
    label: 'PRÓXIMAMENTE',
    reason: 'Requiere Kai Bridge/Nervous Link autorizado'
  });
});
