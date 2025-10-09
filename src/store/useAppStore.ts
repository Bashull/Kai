import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { AppState } from '../types';

import { createUISlice } from './slices/createUISlice';
import { createChatSlice } from './slices/createChatSlice';
import { createKernelSlice } from './slices/createKernelSlice';
import { createForgeSlice } from './slices/createForgeSlice';
import { createStudioSlice } from './slices/createStudioSlice';
import { createCodeSlice } from './slices/createCodeSlice';
import { createImageSlice } from './slices/createImageSlice';

export const useAppStore = create<AppState>()(
  persist(
    (set, get, api) => ({
      ...createUISlice(set, get, api),
      ...createChatSlice(set, get, api),
      ...createKernelSlice(set, get, api),
      ...createForgeSlice(set, get, api),
      ...createStudioSlice(set, get, api),
      ...createCodeSlice(set, get, api),
      ...createImageSlice(set, get, api),
    }),
    {
      name: 'kai-genesis-storage',
      storage: createJSONStorage(() => localStorage),
      // Persist only the UI settings and language preference
      partialize: (state) => ({
        activePanel: state.activePanel,
        sidebarCollapsed: state.sidebarCollapsed,
        theme: state.theme,
        codeLanguage: state.codeLanguage,
      }),
    }
  )
);
