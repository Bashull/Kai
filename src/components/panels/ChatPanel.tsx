import React, { useState, useRef, useEffect } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { streamChat } from '../../services/geminiService';
import MarkdownRenderer from '../ui/MarkdownRenderer';
import { Send } from 'lucide-react';
import { formatRelativeTime } from '../../utils/helpers';
import Button from '../ui/Button';

const ChatPanel: React.FC = () => {
  const [input, setInput] = useState('');
  const { addChatMessage, updateLastChatMessage, setTyping, isTyping, chatHistory } = useAppStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [chatHistory]);

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;

    const userMessageContent = input;
    addChatMessage({ role: 'user', content: userMessageContent });
    setInput('');
    setTyping(true);
    addChatMessage({ role: 'model', content: '' });

    try {
        const historyForAPI = useAppStore.getState().chatHistory.slice(0, -1).map(msg => ({
            role: msg.role,
            parts: [{ text: msg.content }]
        }));

        const stream = await streamChat(historyForAPI, userMessageContent);
        for await (const chunk of stream) {
            updateLastChatMessage(chunk.text);
        }
    } catch (error) {
      console.error(error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      updateLastChatMessage(`\n\n**Error:** Lo siento, he encontrado un error. ${errorMessage}`);
    } finally {
      setTyping(false);
    }
  };
  
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
    }
  }

  return (
    <div>
      <h1 className="h1-title">Chat con Kai</h1>
      <p className="p-subtitle">Nuestro canal de comunicación directa. Estoy listo para colaborar.</p>
      
      <div className="w-full max-w-4xl mx-auto flex flex-col h-[calc(100vh-15rem)]">
        <div className="flex-1 overflow-y-auto pr-4 -mr-4 mb-4">
            <div className="space-y-6">
                {chatHistory.map((msg) => (
                    <div key={msg.id} className={`flex items-start gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                        {msg.role === 'model' && <span className="text-xl mt-1">🤖</span>}
                        <div className={`max-w-xl rounded-xl px-4 py-3 shadow-md ${msg.role === 'user' ? 'bg-kai-primary text-white' : 'bg-kai-surface'}`}>
                            <MarkdownRenderer content={msg.content} />
                            <div className="text-xs mt-2 opacity-60 text-right">
                                {formatRelativeTime(msg.timestamp)}
                            </div>
                        </div>
                    </div>
                ))}
                 {isTyping && chatHistory[chatHistory.length - 1]?.role === 'model' && (
                    <div className="flex items-start gap-3">
                         <span className="text-xl mt-1">🤖</span>
                         <div className="max-w-xl rounded-xl px-4 py-3 bg-kai-surface flex items-center">
                            <span className="animate-pulse">...</span>
                         </div>
                    </div>
                 )}
                <div ref={messagesEndRef} />
            </div>
        </div>
        <div className="relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Envíame un mensaje..."
            className="form-textarea w-full pr-16"
            rows={2}
            disabled={isTyping}
          />
          <Button 
            onClick={handleSend} 
            disabled={!input.trim() || isTyping} 
            loading={isTyping}
            className="absolute right-3 top-1/2 -translate-y-1/2 !p-2 !h-9 !w-9 !rounded-full"
            aria-label="Enviar mensaje"
          >
            {!isTyping && <Send className="h-5 w-5" />}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ChatPanel;