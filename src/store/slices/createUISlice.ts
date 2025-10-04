import { UISlice, AppSlice, Panel, Theme } from '../../types';

export const createUISlice: AppSlice<UISlice> = (set) => ({
  activePanel: 'chat',
  sidebarCollapsed: false,
  theme: 'dark',
  setActivePanel: (panel: Panel) => set({ activePanel: panel }),
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setTheme: (theme: Theme) => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    set({ theme });
  },
});