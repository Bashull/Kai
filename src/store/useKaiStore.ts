

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { KaiState, ChatMessage, GeneratedImage, Entity, EntityStatus, TrainingJob, TrainingJobStatus } from '../types';
import { generateId } from '../utils/helpers';

export const useKaiStore = create<KaiState>()(
  persist(
    (set, get) => ({
      // App state
      activePanel: 'chat',
      sidebarCollapsed: false,
      theme: 'dark',
      
      // Chat state
      isTyping: false,
      chatHistory: [],

      // Code state
      codePrompt: '',
      generatedCode: '',
      codeLanguage: 'javascript',
      isGeneratingCode: false,
      
      // Image state
      imagePrompt: '',
      generatedImages: [],
      isGeneratingImages: false,

      // Kernel state
      entities: [],

      // Forge state
      trainingJobs: [],

      // Actions
      setActivePanel: (panel) => set({ activePanel: panel }),
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setTheme: (theme) => set({ theme }),

      addChatMessage: (message: Pick<ChatMessage, 'role' | 'content'>) => set((state) => ({
        chatHistory: [...state.chatHistory, {
            ...message,
            id: generateId(),
            timestamp: new Date().toISOString(),
        }]
      })),
      updateLastChatMessage: (content: string) => set((state) => {
        const newHistory = [...state.chatHistory];
        if (newHistory.length > 0) {
          newHistory[newHistory.length - 1].content += content;
        }
        return { chatHistory: newHistory };
      }),
      setTyping: (isTyping) => set({ isTyping }),

      setCodePrompt: (prompt) => set({ codePrompt: prompt }),
      setGeneratedCode: (code) => set({ generatedCode: code }),
      setCodeLanguage: (language) => set({ codeLanguage: language }),
      setIsGeneratingCode: (isGenerating) => set({ isGeneratingCode: isGenerating }),
      
      setImagePrompt: (prompt) => set({ imagePrompt: prompt }),
      setGeneratedImages: (images: GeneratedImage[]) => set({ generatedImages: images }),
      setIsGeneratingImages: (isGenerating) => set({ isGeneratingImages: isGenerating }),

      // Kernel actions
      addEntity: (entity) => {
          const newEntity: Entity = {
              ...entity,
              id: generateId(),
              status: 'ASSIMILATING',
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
          };
          set((state) => ({ entities: [newEntity, ...state.entities] }));

          // Simulate assimilation process
          const assimilationTime = Math.random() * 4000 + 2000; // 2-6 seconds
          setTimeout(() => {
              const success = Math.random() > 0.1; // 90% success rate
              get().updateEntityStatus(newEntity.id, success ? 'INTEGRATED' : 'REJECTED');
          }, assimilationTime);
      },
      updateEntityStatus: (entityId, status) => set((state) => ({
          entities: state.entities.map(e => 
              e.id === entityId ? { ...e, status, updatedAt: new Date().toISOString() } : e
          ),
      })),
      
      // Forge actions
      addTrainingJob: (job) => {
        const newJob: TrainingJob = {
          ...job,
          id: generateId(),
          status: 'QUEUED',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };
        set(state => ({ trainingJobs: [newJob, ...state.trainingJobs]}));

        // Simulate training process
        setTimeout(() => {
          get().updateTrainingJobStatus(newJob.id, 'TRAINING');
          const trainingTime = Math.random() * 8000 + 5000; // 5-13 seconds
          setTimeout(() => {
            const success = Math.random() > 0.15; // 85% success rate
            get().updateTrainingJobStatus(newJob.id, success ? 'COMPLETED' : 'FAILED');
          }, trainingTime);
        }, 2000); // 2s queue time
      },
      updateTrainingJobStatus: (jobId, status) => set(state => ({
        trainingJobs: state.trainingJobs.map(j => 
          j.id === jobId ? { ...j, status, updatedAt: new Date().toISOString() } : j
        ),
      })),

    }),
    {
      name: 'kai-ultra-pro-storage',
      storage: createJSONStorage(() => localStorage),
      // Only persist non-sensitive UI settings
      partialize: (state) => ({
        activePanel: state.activePanel,
        sidebarCollapsed: state.sidebarCollapsed,
        theme: state.theme,
        codeLanguage: state.codeLanguage,
        // entities and jobs are not persisted to reset on refresh for this demo
      }),
    }
  )
);