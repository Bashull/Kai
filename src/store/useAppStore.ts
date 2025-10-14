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
import { createResumeSlice } from './slices/createResumeSlice';
import { createNotificationSlice } from './slices/createNotificationSlice';
import { createSearchSlice } from './slices/createSearchSlice';
import { createAwesomeResourceSlice } from './slices/createAwesomeResourceSlice';
import { createDiarySlice } from './slices/createDiarySlice';
import { createSnapshotSlice } from './slices/createSnapshotSlice';
import { createVoiceSlice } from './slices/createVoiceSlice';
import { createLiveSlice } from './slices/createLiveSlice';

export const useAppStore = create<AppState>()(
  persist(
    (...a) => ({
      ...createUISlice(...a),
      ...createChatSlice(...a),
      ...createVoiceSlice(...a),
      ...createLiveSlice(...a),
      ...createKernelSlice(...a),
      ...createForgeSlice(...a),
      ...createStudioSlice(...a),
      ...createCodeSlice(...a),
      ...createImageSlice(...a),
      ...createTaskSlice(...a),
      ...createConstitutionSlice(...a),
      ...createResumeSlice(...a),
      ...createNotificationSlice(...a),
      ...createSearchSlice(...a),
      ...createAwesomeResourceSlice(...a),
      ...createDiarySlice(...a),
      ...createSnapshotSlice(...a),
    }),
    {
      name: 'kai-os-v3-storage',
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
        resumeData: state.resumeData, // Persist resume data
        diary: state.diary, // Persist diary
        snapshots: state.snapshots, // Persist snapshots
        // FIX: Added critical state slices to persistence to prevent data loss on refresh.
        chatHistory: state.chatHistory,
        entities: state.entities,
        trainingJobs: state.trainingJobs,
      }),
    }
  )
);