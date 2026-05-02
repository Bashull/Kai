import React, { useState, useRef, useEffect } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useAppStore } from '../../store/useAppStore';
import { streamChat } from '../../services/geminiService';
import { runConstitutionalPreflight } from '../../services/constitutionalPreflight';
import MarkdownRenderer from '../ui/MarkdownRenderer';
import { Send, Mic, MicOff, Volume2, VolumeX, Archive, Brain, Globe, Loader2 } from 'lucide-react';
import { formatRelativeTime } from '../../utils/helpers';
import Button from '../ui/Button';
import { motion } from 'framer-motion';
import { INPUT_LIMITS } from '../../config/constants';

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
    isSpeakingLoading,
    spokenMessageId,
    speakMessage,
    stopSpeaking,
    summarizeAndSaveChat,
    isSummarizing,
    thinkingMode,
    toggleThinkingMode,
    grounding,
    setGrounding,
    constitution,
    chi,
    auditChi,
    restoreChi,
    addDiaryEntry,
    addNotification,
  } = useAppStore();

  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: chatHistory.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 140,
    overscan: 4,
  });

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (chatHistory.length > 0) {
      virtualizer.scrollToIndex(chatHistory.length - 1, { align: 'end', behavior: 'smooth' });
    }
  }, [chatHistory.length, isTyping]);

  useEffect(() => {
    return () => stopSpeaking();
  }, [stopSpeaking]);

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;
    if (input.length > INPUT_LIMITS.CHAT_MAX_CHARS) {
      addNotification?.({ type: 'error', message: `El mensaje supera el límite de ${INPUT_LIMITS.CHAT_MAX_CHARS.toLocaleString()} caracteres.` });
      return;
    }

    const userMessageContent = input.trim();

    const touchesCodebase =
      /(c[oó]digo|script|repo|archivo|patch|commit|merge|refactor|bug|fix|implementa|modifica)/i.test(
        userMessageContent
      );
    const touchesMemory =
      /(memoria|recuerda|guarda|absorbe|integra|n[uú]cleo|identidad|constituci[oó]n|chi)/i.test(
        userMessageContent
      );
    const destructive = /(borra|elimina|destruye|wipe|purga|rm -rf|sweep|absorbe todo)/i.test(
      userMessageContent
    );

    const preflight = runConstitutionalPreflight({
      prompt: userMessageContent,
      constitution,
      chi,
      touchesCodebase,
      touchesMemory,
      destructive,
    });

    addChatMessage({ role: 'user', content: userMessageContent });
    setInput('');

    if (preflight.blocked) {
      addChatMessage({
        role: 'model',
        content: `${preflight.suggestedReply ?? 'No voy directo con eso.'}\n\n**Motivos:**\n- ${preflight.verdict.reasons.join('\n- ')}`,
      });

      addDiaryEntry?.({
        type: 'CONSTITUTION',
        content: `Preflight bloqueó una acción: ${preflight.plan.objective}`,
      });

      addNotification?.({
        type: 'info',
        message: 'Kai ha desviado una acción por constitución/CHI.',
      });

      if (chi.mode === 'modo_seguro' || chi.coherence < 0.45) {
        restoreChi?.();
      }

      return;
    }

    setTyping(true);
    addChatMessage({ role: 'model', content: '' });

    try {
      addDiaryEntry?.({
        type: 'CONSTITUTION',
        content: `Preflight aprobado: ${preflight.plan.objective}`,
      });

      const historyForAPI = useAppStore
        .getState()
        .chatHistory.slice(0, -2)
        .map((msg) => ({
          role: msg.role,
          parts: [{ text: msg.content }],
        }));

      const stream = streamChat(
        historyForAPI,
        userMessageContent,
        thinkingMode,
        grounding,
        { constitution, chi }
      );

      for await (const chunk of stream) {
        updateLastChatMessage(chunk.text || '', chunk.sources);
      }

      const audit = auditChi?.();
      if (audit && audit.severity !== 'OPTIMO') {
        addNotification?.({
          type: 'info',
          message: `CHI en ${audit.severity.toLowerCase()}: ${audit.reason}`,
        });
        addDiaryEntry?.({
          type: 'SYSTEM_BOOT',
          content: `CHI ${audit.severity}: ${audit.reason}`,
        });
      }
    } catch (error) {
      console.error(error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      updateLastChatMessage(`\n\n**Error:** Lo siento, he encontrado un error. ${errorMessage}`);
      addNotification?.({
        type: 'error',
        message: 'Error durante el ciclo de chat.',
      });
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
      stopRecording((transcript) => setInput((prev) => prev + transcript));
    } else {
      startRecording();
    }
  };

  const virtualItems = virtualizer.getVirtualItems();

  return (
    <div className="flex flex-col h-full">
      <div className="flex justify-between items-center mb-1">
        <div>
          <h1 className="h1-title">Chat con Kai</h1>
          <p className="p-subtitle">Nuestro canal de comunicación directa. Estoy listo para colaborar.</p>
        </div>
        {chatHistory.length > 6 && (
          <Button
            onClick={summarizeAndSaveChat}
            loading={isSummarizing}
            disabled={isSummarizing || isTyping}
            icon={Archive}
            variant="secondary"
            size="sm"
          >
            Resumir y Guardar
          </Button>
        )}
      </div>

      <div className="w-full max-w-4xl mx-auto flex flex-col flex-grow h-[calc(100vh-15rem)]">
        {/* Virtual message list */}
        <div ref={parentRef} className="flex-1 overflow-y-auto pr-4 -mr-4 mb-4">
          <div
            style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}
          >
            {virtualItems.map((virtualItem) => {
              const msg = chatHistory[virtualItem.index];
              const isLastItem = virtualItem.index === chatHistory.length - 1;
              const isThisMessageSpeakingLoading = isSpeakingLoading && spokenMessageId === msg.id;
              const isThisMessagePlaying = isSpeaking && !isSpeakingLoading && spokenMessageId === msg.id;

              return (
                <div
                  key={msg.id}
                  data-index={virtualItem.index}
                  ref={virtualizer.measureElement}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    transform: `translateY(${virtualItem.start}px)`,
                    paddingBottom: '1.5rem',
                  }}
                >
                  <motion.div
                    initial={isLastItem ? { opacity: 0, y: 10 } : false}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2 }}
                    className={`flex items-start gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}
                  >
                    {msg.role === 'model' && (
                      <div className="flex flex-col items-center gap-2 flex-shrink-0">
                        <span className="text-xl mt-1" aria-hidden="true">🤖</span>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="!p-1"
                          onClick={() =>
                            isSpeaking && spokenMessageId === msg.id
                              ? stopSpeaking()
                              : speakMessage(msg.id, msg.content)
                          }
                          title={
                            isThisMessageSpeakingLoading
                              ? 'Generando audio...'
                              : isThisMessagePlaying
                              ? 'Detener lectura'
                              : 'Leer en voz alta'
                          }
                          aria-label={
                            isThisMessageSpeakingLoading
                              ? 'Generando audio'
                              : isThisMessagePlaying
                              ? 'Detener lectura'
                              : 'Leer en voz alta'
                          }
                        >
                          {isThisMessageSpeakingLoading ? (
                            <Loader2 size={14} className="animate-spin" />
                          ) : isThisMessagePlaying ? (
                            <VolumeX size={14} />
                          ) : (
                            <Volume2 size={14} />
                          )}
                        </Button>
                      </div>
                    )}

                    <div
                      className={`max-w-xl rounded-xl px-4 py-3 shadow-md ${
                        msg.role === 'user'
                          ? 'bg-gradient-to-br from-kai-primary to-indigo-600 text-white'
                          : 'bg-kai-surface'
                      } ${isThisMessagePlaying ? 'speaking-highlight' : ''}`}
                    >
                      <MarkdownRenderer content={msg.content} />
                      {msg.sources && msg.sources.length > 0 && (
                        <div className="mt-3 pt-2 border-t border-white/20">
                          <h4 className="text-xs font-bold mb-1">Fuentes:</h4>
                          <ul className="space-y-1">
                            {msg.sources.map((source, i) => (
                              <li key={i}>
                                <a
                                  href={source.uri}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-xs text-cyan-300 hover:underline truncate block"
                                  aria-label={`Fuente: ${source.title}`}
                                >
                                  {i + 1}. {source.title}
                                </a>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      <div className="text-xs mt-2 opacity-60 text-right">{formatRelativeTime(msg.timestamp)}</div>
                    </div>
                  </motion.div>
                </div>
              );
            })}
          </div>

          {/* Typing indicator (outside the virtual list, always at bottom) */}
          {isTyping &&
            chatHistory.length > 0 &&
            chatHistory[chatHistory.length - 1]?.role === 'model' &&
            chatHistory[chatHistory.length - 1]?.content === '' && (
              <div className="flex items-start gap-3 px-1 py-2">
                <span className="text-xl mt-1" aria-hidden="true">🤖</span>
                <div className="max-w-xl rounded-xl px-4 py-3 bg-kai-surface flex items-center">
                  <span className="animate-pulse">...</span>
                </div>
              </div>
            )}
        </div>

        <div className="space-y-2">
          <div className="flex justify-end items-center gap-4 px-2">
            <div className="flex items-center gap-2">
              <label
                htmlFor="thinking-mode"
                className={`text-xs font-medium transition-colors ${
                  thinkingMode ? 'text-kai-primary' : 'text-text-secondary'
                }`}
              >
                Modo Pensamiento
              </label>
              <button
                id="thinking-mode"
                onClick={toggleThinkingMode}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                  thinkingMode ? 'bg-kai-primary' : 'bg-gray-600'
                }`}
              >
                <motion.span
                  layout
                  className="inline-block h-3.5 w-3.5 transform rounded-full bg-white"
                  style={{ x: thinkingMode ? '1.1rem' : '0.1rem' }}
                />
                <Brain size={10} className={`absolute text-gray-800 ${thinkingMode ? 'left-1' : 'right-1'}`} />
              </button>
            </div>

            <div className="flex items-center gap-2">
              <label
                htmlFor="grounding-mode"
                className={`text-xs font-medium transition-colors ${
                  grounding === 'web' ? 'text-cyan-400' : 'text-text-secondary'
                }`}
              >
                Búsqueda Web
              </label>
              <button
                id="grounding-mode"
                onClick={() => setGrounding(grounding === 'web' ? 'none' : 'web')}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                  grounding === 'web' ? 'bg-cyan-500' : 'bg-gray-600'
                }`}
              >
                <motion.span
                  layout
                  className="inline-block h-3.5 w-3.5 transform rounded-full bg-white"
                  style={{ x: grounding === 'web' ? '1.1rem' : '0.1rem' }}
                />
                <Globe size={10} className={`absolute text-gray-800 ${grounding === 'web' ? 'left-1' : 'right-1'}`} />
              </button>
            </div>
          </div>

          <div className="relative">
            {isRecording && (
              <div className="absolute inset-x-0 -top-10 flex justify-center items-center">
                <div className="bg-kai-surface px-4 py-2 rounded-lg flex items-center gap-2 text-sm text-text-secondary shadow-lg">
                  <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                  <span>Grabando...</span>
                </div>
              </div>
            )}

            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value.slice(0, INPUT_LIMITS.CHAT_MAX_CHARS))}
              onKeyDown={handleKeyDown}
              placeholder={isRecording ? '' : 'Envíame un mensaje...'}
              className="form-textarea w-full pr-28"
              rows={2}
              disabled={isTyping}
              aria-label="Mensaje de chat"
              maxLength={INPUT_LIMITS.CHAT_MAX_CHARS}
            />
            {input.length > INPUT_LIMITS.CHAT_MAX_CHARS * 0.9 && (
              <span className="absolute bottom-1 left-3 text-xs text-yellow-400">
                {input.length}/{INPUT_LIMITS.CHAT_MAX_CHARS}
              </span>
            )}

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
    </div>
  );
};

export default ChatPanel;
