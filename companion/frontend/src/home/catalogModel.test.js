import { groupBySection, searchCatalog, primaryAction } from './catalogModel';

const item = {
  id: 'skin-anime', title: 'Minecraft → Anime', kind: 'app',
  sections: ['APLICACIONES', 'CREACIÓN VISUAL'], status: 'FUNCTIONAL',
  description: 'Generador anime', tags: ['minecraft', 'anime'],
  launch_kind: 'web_app', launch_target: '/apps/skin-anime', continue_target: null
};

test('same object can appear in multiple sections without duplication', () => {
  const grouped = groupBySection([item]);
  expect(grouped.APLICACIONES[0]).toBe(item);
  expect(grouped['CREACIÓN VISUAL'][0]).toBe(item);
});

test('search matches title and tags case-insensitively', () => {
  expect(searchCatalog([item], 'MINECRAFT')).toEqual([item]);
  expect(searchCatalog([item], 'anime')).toEqual([item]);
});

test('functional item prefers USAR', () => {
  expect(primaryAction(item)).toEqual({ label: 'USAR', target: '/apps/skin-anime', kind: 'web_app' });
});
