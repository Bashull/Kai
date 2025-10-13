import { UISlice, AppSlice, Panel, Theme, Task } from '../../types';

export const createUISlice: AppSlice<UISlice> = (set) => ({
  activePanel: 'chat',
  sidebarCollapsed: false,
  theme: 'dark',
  dueTasks: [],
  showNotifications: false,
  setActivePanel: (panel: Panel) => set({ activePanel: panel }),
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  // FIX: The setTheme action is now a pure function that only updates the state.
  // All DOM-related side-effects have been moved to a useEffect hook in the
  // App component, which listens for theme changes. This separation of concerns
  // resolves the infinite re-render loop.
  setTheme: (theme: Theme) => set({ theme }),
  setDueTasks: (tasks: Task[]) => set({ dueTasks: tasks }),
  toggleNotifications: () => set((state) => ({ showNotifications: !state.showNotifications })),
});