import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { AppState } from '../types';
import { STORAGE_LIMITS } from '../config/constants';
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
import { createEvolutionSlice } from './slices/createEvolutionSlice';
import { createVideoSlice } from './slices/createVideoSlice';
import { createAnalysisSlice } from './slices/createAnalysisSlice';
import { createChiSlice } from './slices/createChiSlice';

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
      ...createVideoSlice(...a),
      ...createAnalysisSlice(...a),
      ...createTaskSlice(...a),
      ...createConstitutionSlice(...a),
      ...createResumeSlice(...a),
      ...createNotificationSlice(...a),
      ...createSearchSlice(...a),
      ...createAwesomeResourceSlice(...a),
      ...createDiarySlice(...a),
      ...createSnapshotSlice(...a),
      ...createEvolutionSlice(...a),
      ...createChiSlice(...a),
    }),
    {
      name: 'kai-os-v3-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        activePanel: state.activePanel,
        sidebarCollapsed: state.sidebarCollapsed,
        theme: state.theme,
        codeLanguage: state.codeLanguage,
        tasks: state.tasks,
        constitution: state.constitution,
        versionHistory: state.versionHistory,
        resumeData: state.resumeData,
        diary: state.diary.slice(-STORAGE_LIMITS.DIARY),
        snapshots: state.snapshots.slice(-STORAGE_LIMITS.SNAPSHOTS),
        chatHistory: state.chatHistory.slice(-STORAGE_LIMITS.CHAT_HISTORY),
        entities: state.entities.slice(-STORAGE_LIMITS.ENTITIES),
        trainingJobs: state.trainingJobs.slice(-STORAGE_LIMITS.TRAINING_JOBS),
        chi: state.chi,
        chiAudit: state.chiAudit,
      }),
    }
  )
);