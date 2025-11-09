import { MemorySlice, AppSlice, Memory } from '../../types';
import { generateId } from '../../utils/helpers';

export const createMemorySlice: AppSlice<MemorySlice> = (set, get) => ({
  memories: [],
  
  addMemory: (memory) =>
    set((state) => ({
      memories: [
        {
          ...memory,
          id: generateId(),
          timestamp: new Date().toISOString(),
        },
        ...state.memories,
      ],
    })),

  updateMemory: (id, updates) =>
    set((state) => ({
      memories: state.memories.map((m) =>
        m.id === id ? { ...m, ...updates } : m
      ),
    })),

  deleteMemory: (id) =>
    set((state) => ({
      memories: state.memories.filter((m) => m.id !== id),
    })),

  searchMemories: (query) => {
    const memories = get().memories;
    const lowerQuery = query.toLowerCase();
    return memories.filter(
      (m) =>
        m.content.toLowerCase().includes(lowerQuery) ||
        m.tags?.some((tag) => tag.toLowerCase().includes(lowerQuery))
    );
  },

  getRecentMemories: (count) => {
    const memories = get().memories;
    return memories.slice(0, count);
  },

  getMemoriesByType: (type) => {
    const memories = get().memories;
    return memories.filter((m) => m.type === type);
  },
});
