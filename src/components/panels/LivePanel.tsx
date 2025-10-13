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
        currentOutputTranscription,
        analyserNode
    } = useAppStore();
    const transcriptionEndRef = useRef<HTMLDivElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const animationFrameIdRef = useRef<number | null>(null);

    useEffect(() => {
        // Cleanup on unmount
        return () => {
            disconnectFromLive();
        };
    }, [disconnectFromLive]);

    useEffect(() => {
        transcriptionEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [transcriptionHistory, currentInputTranscription, currentOutputTranscription]);

    useEffect(() => {
        if (!isConnected || !analyserNode || !canvasRef.current) {
            if (animationFrameIdRef.current) {
                cancelAnimationFrame(animationFrameIdRef.current);
                animationFrameIdRef.current = null;
            }
            return;
        }

        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const bufferLength = analyserNode.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        const draw = () => {
            animationFrameIdRef.current = requestAnimationFrame(draw);

            analyserNode.getByteFrequencyData(dataArray);

            const width = canvas.width;
            const height = canvas.height;
            const centerX = width / 2;
            const centerY = height / 2;
            
            let sum = 0;
            for(let i = 0; i < bufferLength; i++) {
                sum += dataArray[i];
            }
            const avg = sum / bufferLength;

            ctx.clearRect(0, 0, width, height);

            const baseRadius = 40;
            const maxRadius = 75;
            const radius = Math.min(baseRadius + (avg / 255) * (maxRadius - baseRadius) * 2, maxRadius);

            // Draw pulsating outer circles
            for (let i = 1; i <= 3; i++) {
                ctx.beginPath();
                ctx.arc(centerX, centerY, radius + i * 20, 0, 2 * Math.PI);
                const opacity = Math.max(0, (avg / 128) - (i * 0.2));
                ctx.strokeStyle = `rgba(79, 70, 229, ${opacity * 0.5})`;
                ctx.lineWidth = 2;
                ctx.stroke();
            }

            // Draw central orb
            const grd = ctx.createRadialGradient(centerX, centerY, radius * 0.5, centerX, centerY, radius);
            grd.addColorStop(0, '#4f46e5');
            grd.addColorStop(1, '#39ff14');
            
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
            ctx.fillStyle = grd;
            ctx.fill();
        };

        draw();

        return () => {
            if (animationFrameIdRef.current) {
                cancelAnimationFrame(animationFrameIdRef.current);
            }
        };
    }, [isConnected, analyserNode]);

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
                 <div
                    onClick={handleToggleConnection}
                    className="relative w-40 h-40 flex items-center justify-center cursor-pointer group"
                    role="button"
                    aria-label={isConnected ? "Detener conversación" : "Iniciar conversación"}
                >
                    <canvas ref={canvasRef} width="160" height="160" className="absolute inset-0"></canvas>
                    <div className={`relative z-10 w-24 h-24 rounded-full flex items-center justify-center transition-all duration-300 ${isConnected ? 'bg-red-500/80 group-hover:bg-red-600/80' : 'bg-kai-primary/80 group-hover:bg-kai-primary/90'}`}>
                         {isConnecting ? (
                            <div className="w-12 h-12 border-4 border-white/50 border-t-white rounded-full animate-spin"></div>
                         ) : (
                            <>
                                {isConnected ? (
                                    <StopCircle className="w-12 h-12 text-white" />
                                ) : (
                                    <Mic className="w-12 h-12 text-white" />
                                )}
                            </>
                         )}
                    </div>
                </div>
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