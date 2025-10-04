import { ChatSlice, AppSlice, ChatMessage } from '../../types';
import { generateId } from '../../utils/helpers';

export const createChatSlice: AppSlice<ChatSlice> = (set) => ({
  isTyping: false,
  chatHistory: [],
  addChatMessage: (message: Pick<ChatMessage, 'role' | 'content'>) =>
    set((state) => ({
      chatHistory: [
        ...state.chatHistory,
        {
          ...message,
          id: generateId(),
          timestamp: new Date().toISOString(),
        },
      ],
    })),
  updateLastChatMessage: (content: string) =>
    set((state) => {
      const newHistory = [...state.chatHistory];
      if (newHistory.length > 0) {
        newHistory[newHistory.length - 1].content += content;
      }
      return { chatHistory: newHistory };
    }),
  setTyping: (isTyping: boolean) => set({ isTyping }),
});