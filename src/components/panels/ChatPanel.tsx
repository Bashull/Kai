import React, { useState, useRef, useEffect } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { streamChat } from '../../services/geminiService';
import MarkdownRenderer from '../ui/MarkdownRenderer';
import { Send, Mic, MicOff, Volume2, VolumeX } from 'lucide-react';
import { formatRelativeTime } from '../../utils/helpers';
import Button from '../ui/Button';
import { AnimatePresence, motion } from 'framer-motion';

const ChatPanel: React.FC = () => {
  const [input, setInput] = useState('');
  const { 
    addChatMessage, 
    updateLastChatMessage, 
    setTyping, 
    isTyping, 
    chatHistory,
    isRecording,
    startRecording,
    stopRecording,
    isSpeaking,
    spokenMessageId,
    speakMessage,
    stopSpeaking,
  } = useAppStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [chatHistory, isTyping]);
  
  // Clean up speech synthesis on component unmount
  useEffect(() => {
    return () => stopSpeaking();
  }, [stopSpeaking]);

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;

    const userMessageContent = input;
    addChatMessage({ role: 'user', content: userMessageContent });
    setInput('');
    setTyping(true);
    addChatMessage({ role: 'model', content: '' });

    try {
        const historyForAPI = useAppStore.getState().chatHistory.slice(0, -2).map(msg => ({
            role: msg.role,
            parts: [{ text: msg.content }]
        }));

        const stream = streamChat(historyForAPI, userMessageContent);
        for await (const chunk of stream) {
            updateLastChatMessage(chunk);
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
  };

  const handleVoiceRecording = () => {
    if (isRecording) {
        stopRecording((transcript) => {
            setInput(prev => prev + transcript);
        });
    } else {
        startRecording();
    }
  };

  return (
    <div>
      <h1 className="h1-title">Chat con Kai</h1>
      <p className="p-subtitle">Nuestro canal de comunicación directa. Estoy listo para colaborar.</p>
      
      <div className="w-full max-w-4xl mx-auto flex flex-col h-[calc(100vh-15rem)]">
        <div className="flex-1 overflow-y-auto pr-4 -mr-4 mb-4">
            <div className="space-y-6">
                <AnimatePresence>
                    {chatHistory.map((msg) => (
                        <motion.div
                            layout
                            key={msg.id}
                            initial={{ opacity: 0, y: 15, scale: 0.95 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.9 }}
                            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                            className={`flex items-start gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}
                        >
                            {msg.role === 'model' && (
                                <div className="flex flex-col items-center gap-2">
                                    <span className="text-xl mt-1" aria-hidden="true">🤖</span>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="!p-1"
                                      onClick={() => isSpeaking && spokenMessageId === msg.id ? stopSpeaking() : speakMessage(msg.id, msg.content)}
                                      title={isSpeaking && spokenMessageId === msg.id ? 'Detener lectura' : 'Leer en voz alta'}
                                    >
                                        {isSpeaking && spokenMessageId === msg.id ? <VolumeX size={14} /> : <Volume2 size={14} />}
                                    </Button>
                                </div>
                            )}
                            <div className={`max-w-xl rounded-xl px-4 py-3 shadow-md ${
                                msg.role === 'user' 
                                    ? 'bg-gradient-to-br from-kai-primary to-indigo-600 text-white chat-bubble-user' 
                                    : 'bg-kai-surface chat-bubble-model'
                            }`}>
                                <MarkdownRenderer content={msg.content} />
                                <div className="text-xs mt-2 opacity-60 text-right">
                                    {formatRelativeTime(msg.timestamp)}
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>
                 {isTyping && chatHistory.length > 0 && chatHistory[chatHistory.length - 1]?.role === 'model' && chatHistory[chatHistory.length - 1]?.content === '' && (
                    <div className="flex items-start gap-3">
                         <span className="text-xl mt-1" aria-hidden="true">🤖</span>
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
            placeholder="Envíame un mensaje o utiliza el micrófono..."
            className="form-textarea w-full pr-28"
            rows={2}
            disabled={isTyping}
            aria-label="Mensaje de chat"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
            <Button
              onClick={handleVoiceRecording}
              className={`!p-2 !h-9 !w-9 !rounded-full ${isRecording ? 'bg-red-500 hover:bg-red-600' : ''}`}
              title={isRecording ? 'Detener grabación' : 'Grabar voz'}
            >
              {isRecording ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
            </Button>
            <Button 
              onClick={handleSend} 
              disabled={!input.trim() || isTyping} 
              loading={isTyping}
              className="!p-2 !h-9 !w-9 !rounded-full"
              aria-label="Enviar mensaje"
            >
              {!isTyping && <Send className="h-5 w-5" />}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPanel;