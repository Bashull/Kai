import { resolveLaunch, safeBrowserHref } from './launch';

test('local app is never launched by browser in v0.1', () => {
  expect(resolveLaunch({ launch_kind: 'local_app_future', launch_target: 'C:/unsafe.exe' })).toEqual({
    enabled: false,
    href: null,
    label: 'PRÓXIMAMENTE',
    reason: 'Requiere Kai Bridge/Nervous Link autorizado'
  });
});

test('browser href rejects protocol-relative and backslash authority tricks', () => {
  expect(safeBrowserHref('//kai.home.invalid/path')).toBeNull();
  expect(safeBrowserHref(String.raw`/\kai.home.invalid/path`)).toBeNull();
});
