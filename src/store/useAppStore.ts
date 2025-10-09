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
import { createTaskSlice } from './slices/createTaskSlice';
import { createConstitutionSlice } from './slices/createConstitutionSlice';

export const useAppStore = create<AppState>()(
  persist(
    (...a) => ({
      ...createUISlice(...a),
      ...createChatSlice(...a),
      ...createKernelSlice(...a),
      ...createForgeSlice(...a),
      ...createStudioSlice(...a),
      ...createCodeSlice(...a),
      ...createImageSlice(...a),
      ...createTaskSlice(...a),
      ...createConstitutionSlice(...a),
    }),
    {
      name: 'kai-ultra-pro-storage',
      storage: createJSONStorage(() => localStorage),
      // Only persist non-sensitive UI settings and important data
      partialize: (state) => ({
        activePanel: state.activePanel,
        sidebarCollapsed: state.sidebarCollapsed,
        theme: state.theme,
        codeLanguage: state.codeLanguage,
        tasks: state.tasks, // Persist user's tasks
        constitution: state.constitution, // Persist constitution
        versionHistory: state.versionHistory, // Persist history
      }),
    }
  )
);