import { ChatSlice, AppSlice, ChatMessage } from '../../types';
import { generateId } from '../../utils/helpers';
import { summarizeText } from '../../services/geminiService';

export const createChatSlice: AppSlice<ChatSlice> = (set, get) => ({
  isTyping: false,
  chatHistory: [],
  isSummarizing: false,
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
      if (newHistory.length > 0 && newHistory[newHistory.length - 1].role === 'model') {
        newHistory[newHistory.length - 1].content += content;
      }
      return { chatHistory: newHistory };
    }),
  setTyping: (isTyping: boolean) => set({ isTyping }),
  summarizeAndSaveChat: async () => {
    const { chatHistory, addEntity, addNotification, addMemory, addDiaryEntry } = get();
    if (chatHistory.length < 2) {
      addNotification({ type: 'info', message: 'No hay suficiente conversación para resumir.' });
      return;
    }

    set({ isSummarizing: true });
    try {
      const conversationText = chatHistory
        .map(msg => `${msg.role === 'user' ? 'Compañero' : 'Kai'}: ${msg.content}`)
        .join('\n');
      
      const summary = await summarizeText(conversationText);

      // Save to Kernel
      addEntity({
        content: summary,
        type: 'TEXT',
        source: 'Chat Summary',
      });

      // Save to long-term Memory
      addMemory({
        content: summary,
        type: 'CONVERSATION',
        importance: 0.7,
        tags: ['chat', 'conversation', 'summary'],
        metadata: {
          messageCount: chatHistory.length,
          date: new Date().toISOString(),
        },
      });

      // Add diary entry
      addDiaryEntry({
        type: 'KERNEL',
        content: `Conversación resumida y guardada en memoria a largo plazo (${chatHistory.length} mensajes).`,
      });

      addNotification({ type: 'success', message: 'Resumen guardado en Kernel y Memoria a largo plazo.' });

    } catch (error) {
        console.error("Failed to summarize chat:", error);
        addNotification({ type: 'error', message: 'No se pudo generar el resumen.' });
    } finally {
        set({ isSummarizing: false });
    }
  },
});
