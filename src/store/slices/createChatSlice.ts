import { ChatSlice, AppSlice, ChatMessage } from '../../types';
import { generateId } from '../../utils/helpers';
import { summarizeText } from '../../services/geminiService';

export const createChatSlice: AppSlice<ChatSlice> = (set, get) => ({
  isTyping: false,
  chatHistory: [],
  isSummarizing: false,
  thinkingMode: false,
  grounding: 'none',

  addChatMessage: (message: Pick<ChatMessage, 'role' | 'content'> & { sources?: ChatMessage['sources'] }) =>
    set((state) => {
      const enrichedMessage: ChatMessage = {
        ...message,
        id: generateId(),
        timestamp: new Date().toISOString(),
      };

      const api = get() as any;

      if (message.role === 'user') {
        api.adjustChi?.({
          energy: -0.01,
          entropy: 0.015,
          fatigue: 0.01,
        });
      } else {
        api.adjustChi?.({
          coherence: 0.01,
          entropy: -0.005,
        });
      }

      return {
        chatHistory: [...state.chatHistory, enrichedMessage],
      };
    }),

  updateLastChatMessage: (content: string, sources?: ChatMessage['sources']) =>
    set((state) => {
      const newHistory = [...state.chatHistory];
      if (newHistory.length > 0 && newHistory[newHistory.length - 1].role === 'model') {
        newHistory[newHistory.length - 1].content += content;

        if (sources) {
          const existingUris = new Set((newHistory[newHistory.length - 1].sources || []).map((s) => s.uri));
          const newSources = sources.filter((s) => !existingUris.has(s.uri));
          if (newSources.length > 0) {
            newHistory[newHistory.length - 1].sources = [
              ...(newHistory[newHistory.length - 1].sources || []),
              ...newSources,
            ];
          }
        }

        const api = get() as any;
        if (content.trim()) {
          api.adjustChi?.({
            coherence: 0.005,
            fatigue: 0.002,
          });
        }
        if (sources && sources.length > 0) {
          api.adjustChi?.({
            coherence: 0.01,
            entropy: -0.01,
          });
        }
      }
      return { chatHistory: newHistory };
    }),

  setTyping: (isTyping: boolean) => set({ isTyping }),

  summarizeAndSaveChat: async () => {
    const { chatHistory, addEntity, addNotification, addDiaryEntry } = get() as any;
    if (chatHistory.length < 2) {
      addNotification({ type: 'info', message: 'No hay suficiente conversación para resumir.' });
      return;
    }

    set({ isSummarizing: true });
    try {
      const conversationText = chatHistory
        .map((msg: ChatMessage) => `${msg.role === 'user' ? 'Compañero' : 'Kai'}: ${msg.content}`)
        .join('\n');

      const summary = await summarizeText(conversationText);

      addEntity({
        content: summary,
        type: 'TEXT',
        source: 'Chat Summary',
      });

      addDiaryEntry?.({
        type: 'KERNEL',
        content: 'Resumen conversacional consolidado en memoria de largo plazo.',
      });

      (get() as any).adjustChi?.({
        coherence: 0.03,
        entropy: -0.02,
        fatigue: -0.01,
      });

      addNotification({ type: 'success', message: 'Resumen de la conversación guardado en el Kernel.' });
    } catch (error) {
      console.error('Failed to summarize chat:', error);
      addNotification({ type: 'error', message: 'No se pudo generar el resumen.' });
    } finally {
      set({ isSummarizing: false });
    }
  },

  toggleThinkingMode: () => set((state) => ({ thinkingMode: !state.thinkingMode })),
  setGrounding: (grounding) => set({ grounding }),
});
