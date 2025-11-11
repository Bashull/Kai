import React, { useState, useRef, useEffect } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { streamChat } from '../../services/geminiService';
import MarkdownRenderer from '../ui/MarkdownRenderer';
import { Send, Mic, MicOff, Volume2, VolumeX, Archive, Brain, Globe } from 'lucide-react';
import { formatRelativeTime } from '../../utils/helpers';
import Button from '../ui/Button';
import { AnimatePresence, motion } from 'framer-motion';

const ChatPanel: React.FC = () => {
  const [input, setInput] = useState('');
  const { 
    addChatMessage, updateLastChatMessage, setTyping, isTyping, chatHistory,
    isRecording, startRecording, stopRecording,
    isSpeaking, spokenMessageId, speakMessage, stopSpeaking,
    summarizeAndSaveChat, isSummarizing,
    thinkingMode, toggleThinkingMode, grounding, setGrounding
  } = useAppStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, isTyping]);
  
  useEffect(() => { return () => stopSpeaking(); }, [stopSpeaking]);

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;
    const userMessageContent = input;
    addChatMessage({ role: 'user', content: userMessageContent });
    setInput('');
    setTyping(true);
    addChatMessage({ role: 'model', content: '' });

    try {
        const historyForAPI = useAppStore.getState().chatHistory.slice(0, -2).map(msg => ({
            role: msg.role, parts: [{ text: msg.content }]
        }));
        const stream = streamChat(historyForAPI, userMessageContent, thinkingMode, grounding);
        for await (const chunk of stream) {
            updateLastChatMessage(chunk.text || '', chunk.sources);
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
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleVoiceRecording = () => {
    if (isRecording) {
        stopRecording((transcript) => setInput(prev => prev + transcript));
    } else {
        startRecording();
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex justify-between items-center mb-1">
        <div>
            <h1 className="h1-title">Chat con Kai</h1>
            <p className="p-subtitle">Nuestro canal de comunicación directa. Estoy listo para colaborar.</p>
        </div>
        {chatHistory.length > 6 && (
            <Button onClick={summarizeAndSaveChat} loading={isSummarizing} disabled={isSummarizing || isTyping} icon={Archive} variant="secondary" size="sm">
                Resumir y Guardar
            </Button>
        )}
      </div>
      
      <div className="w-full max-w-4xl mx-auto flex flex-col flex-grow h-[calc(100vh-15rem)]">
        <div className="flex-1 overflow-y-auto pr-4 -mr-4 mb-4">
            <div className="space-y-6">
                <AnimatePresence>
                    {chatHistory.map((msg) => (
                        <motion.div
                            layout key={msg.id}
                            initial={{ opacity: 0, y: 15, scale: 0.95 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}
                            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                            className={`flex items-start gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}
                        >
                            {msg.role === 'model' && (
                                <div className="flex flex-col items-center gap-2">
                                    <span className="text-xl mt-1" aria-hidden="true">🤖</span>
                                    <Button variant="ghost" size="sm" className="!p-1" onClick={() => isSpeaking && spokenMessageId === msg.id ? stopSpeaking() : speakMessage(msg.id, msg.content)} title={isSpeaking && spokenMessageId === msg.id ? 'Detener lectura' : 'Leer en voz alta'}>
                                        {isSpeaking && spokenMessageId === msg.id ? <VolumeX size={14} /> : <Volume2 size={14} />}
                                    </Button>
                                </div>
                            )}
                            <div className={`max-w-xl rounded-xl px-4 py-3 shadow-md ${ msg.role === 'user' ? 'bg-gradient-to-br from-kai-primary to-indigo-600 text-white' : 'bg-kai-surface'} ${isSpeaking && spokenMessageId === msg.id ? 'speaking-highlight' : ''}`}>
                                <MarkdownRenderer content={msg.content} />
                                {msg.sources && msg.sources.length > 0 && (
                                    <div className="mt-3 pt-2 border-t border-white/20">
                                        <h4 className="text-xs font-bold mb-1">Fuentes:</h4>
                                        <ul className="space-y-1">
                                            {msg.sources.map((source, i) => (
                                                <li key={i}><a href={source.uri} target="_blank" rel="noopener noreferrer" className="text-xs text-cyan-300 hover:underline truncate block">{i + 1}. {source.title}</a></li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                                <div className="text-xs mt-2 opacity-60 text-right">{formatRelativeTime(msg.timestamp)}</div>
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>
                 {isTyping && chatHistory.length > 0 && chatHistory[chatHistory.length - 1]?.role === 'model' && chatHistory[chatHistory.length - 1]?.content === '' && (
                    <div className="flex items-start gap-3">
                         <span className="text-xl mt-1" aria-hidden="true">🤖</span>
                         <div className="max-w-xl rounded-xl px-4 py-3 bg-kai-surface flex items-center"><span className="animate-pulse">...</span></div>
                    </div>
                 )}
                <div ref={messagesEndRef} />
            </div>
        </div>
        <div className="space-y-2">
            <div className="flex justify-end items-center gap-4 px-2">
                <div className="flex items-center gap-2">
                    <label htmlFor="thinking-mode" className={`text-xs font-medium transition-colors ${thinkingMode ? 'text-kai-primary' : 'text-text-secondary'}`}>Modo Pensamiento</label>
                    <button id="thinking-mode" onClick={toggleThinkingMode} className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${thinkingMode ? 'bg-kai-primary' : 'bg-gray-600'}`}>
                        <motion.span layout className="inline-block h-3.5 w-3.5 transform rounded-full bg-white" style={{x: thinkingMode ? '1.1rem' : '0.1rem' }} />
                        <Brain size={10} className={`absolute text-gray-800 ${thinkingMode ? 'left-1' : 'right-1'}`}/>
                    </button>
                </div>
                <div className="flex items-center gap-2">
                    <label htmlFor="grounding-mode" className={`text-xs font-medium transition-colors ${grounding === 'web' ? 'text-cyan-400' : 'text-text-secondary'}`}>Búsqueda Web</label>
                    <button id="grounding-mode" onClick={() => setGrounding(grounding === 'web' ? 'none' : 'web')} className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${grounding === 'web' ? 'bg-cyan-500' : 'bg-gray-600'}`}>
                        <motion.span layout className="inline-block h-3.5 w-3.5 transform rounded-full bg-white" style={{x: grounding === 'web' ? '1.1rem' : '0.1rem' }} />
                        <Globe size={10} className={`absolute text-gray-800 ${grounding === 'web' ? 'left-1' : 'right-1'}`}/>
                    </button>
                </div>
            </div>
            <div className="relative">
              {isRecording && <div className="absolute inset-x-0 -top-10 flex justify-center items-center"><div className="bg-kai-surface px-4 py-2 rounded-lg flex items-center gap-2 text-sm text-text-secondary shadow-lg"><div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div><span>Grabando...</span></div></div>}
              <textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown} placeholder={isRecording ? "" : "Envíame un mensaje..."} className="form-textarea w-full pr-28" rows={2} disabled={isTyping} aria-label="Mensaje de chat"/>
              <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
                <Button onClick={handleVoiceRecording} className={`!p-2 !h-9 !w-9 !rounded-full ${isRecording ? 'bg-red-500 hover:bg-red-600' : ''}`} title={isRecording ? 'Detener grabación' : 'Grabar voz'}>{isRecording ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}</Button>
                <Button onClick={handleSend} disabled={!input.trim() || isTyping} loading={isTyping} className="!p-2 !h-9 !w-9 !rounded-full" aria-label="Enviar mensaje">{!isTyping && <Send className="h-5 w-5" />}</Button>
              </div>
            </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPanel;
