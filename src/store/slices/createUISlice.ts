import { UISlice, AppSlice, Panel, Theme, Task } from '../../types';

export const createUISlice: AppSlice<UISlice> = (set) => ({
  activePanel: 'chat',
  sidebarCollapsed: false,
  theme: 'dark',
  dueTasks: [],
  showNotifications: false,
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
  setDueTasks: (tasks: Task[]) => set({ dueTasks: tasks }),
  toggleNotifications: () => set((state) => ({ showNotifications: !state.showNotifications })),
});