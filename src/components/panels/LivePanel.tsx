import React, { useEffect, useRef } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { motion } from 'framer-motion';
import { Mic, StopCircle, User } from 'lucide-react';
import Button from '../ui/Button';
import KaiAvatar from '../ui/KaiAvatar';

const LivePanel: React.FC = () => {
    const {
        isConnecting,
        isConnected,
        connectToLive,
        disconnectFromLive,
        transcriptionHistory,
        currentInputTranscription,
        currentOutputTranscription
    } = useAppStore();
    const transcriptionEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        // Cleanup on unmount
        return () => {
            disconnectFromLive();
        };
    }, [disconnectFromLive]);

    useEffect(() => {
        transcriptionEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [transcriptionHistory, currentInputTranscription, currentOutputTranscription]);

    const handleToggleConnection = () => {
        if (isConnected) {
            disconnectFromLive();
        } else {
            connectToLive();
        }
    };

    const getStatusText = () => {
        if (isConnecting) return 'Conectando...';
        if (isConnected) return 'Conectado - Habla ahora';
        return 'Desconectado';
    };

    return (
        <div className="flex flex-col h-full text-center">
            <h1 className="h1-title">Conversación en Vivo</h1>
            <p className="p-subtitle">Habla con Kai en tiempo real.</p>
            
            <div className="flex-grow flex flex-col items-center justify-center my-6">
                <Button
                    onClick={handleToggleConnection}
                    disabled={isConnecting}
                    loading={isConnecting}
                    className={`relative w-40 h-40 rounded-full !p-0 transition-all duration-300 ${isConnected ? 'bg-red-500/50 hover:bg-red-600/50 live-glowing' : 'bg-kai-primary/50 hover:bg-kai-primary/60'}`}
                >
                    {isConnected ? (
                        <StopCircle className="w-20 h-20 text-white" />
                    ) : (
                        <Mic className="w-20 h-20 text-white" />
                    )}
                </Button>
                <p className="mt-6 text-lg font-semibold text-text-secondary">{getStatusText()}</p>
            </div>
            
            <div className="w-full max-w-3xl mx-auto h-64 bg-kai-surface/50 rounded-xl p-4 flex flex-col border border-border-color">
                <h3 className="text-sm font-semibold text-text-secondary mb-2 text-left">Transcripción en Vivo</h3>
                <div className="flex-grow overflow-y-auto space-y-4 pr-2 text-left text-sm">
                    {transcriptionHistory.map(entry => (
                        <div key={entry.id} className={`flex items-start gap-3 ${entry.speaker === 'user' ? 'justify-end' : ''}`}>
                            {entry.speaker === 'model' && <KaiAvatar size="sm" className="!w-6 !h-6 mt-0.5" />}
                            <p className={`px-3 py-2 rounded-lg max-w-md ${entry.speaker === 'user' ? 'bg-kai-primary/80 text-white' : 'bg-kai-dark/60'}`}>{entry.text}</p>
                             {entry.speaker === 'user' && <div className="flex-shrink-0 w-6 h-6 mt-0.5 rounded-full bg-kai-surface flex items-center justify-center"><User size={14} /></div>}
                        </div>
                    ))}
                     {currentInputTranscription && (
                         <div className="flex items-start gap-3 justify-end opacity-70">
                            <p className="px-3 py-2 rounded-lg max-w-md bg-kai-primary/60 text-white">{currentInputTranscription}</p>
                            <div className="flex-shrink-0 w-6 h-6 mt-0.5 rounded-full bg-kai-surface flex items-center justify-center"><User size={14} /></div>
                        </div>
                    )}
                    {currentOutputTranscription && (
                        <div className="flex items-start gap-3 opacity-70">
                            <KaiAvatar size="sm" className="!w-6 !h-6 mt-0.5" />
                            <p className="px-3 py-2 rounded-lg max-w-md bg-kai-dark/40">{currentOutputTranscription}</p>
                        </div>
                    )}
                    <div ref={transcriptionEndRef} />
                </div>
            </div>
        </div>
    );
};

export default LivePanel;
