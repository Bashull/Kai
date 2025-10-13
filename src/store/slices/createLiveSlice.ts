import { AppSlice, LiveSlice } from '../../types';
import { GoogleGenAI, LiveServerMessage, Modality, Blob } from '@google/genai';
import { generateId, decode, decodeAudioData, createBlob } from '../../utils/helpers';

// Module-level variables to manage audio contexts and streams
let inputAudioContext: AudioContext | null = null;
let outputAudioContext: AudioContext | null = null;
let scriptProcessor: ScriptProcessorNode | null = null;
let stream: MediaStream | null = null;
let nextStartTime = 0;
const sources = new Set<AudioBufferSourceNode>();

export const createLiveSlice: AppSlice<LiveSlice> = (set, get) => ({
    isConnecting: false,
    isConnected: false,
    session: null,
    transcriptionHistory: [],
    currentInputTranscription: '',
    currentOutputTranscription: '',

    connectToLive: async () => {
        if (get().isConnecting || get().isConnected) return;
        set({ isConnecting: true });

        try {
            const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
            
            // Initialize AudioContexts
            inputAudioContext = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
            outputAudioContext = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
            const outputNode = outputAudioContext.createGain();
            outputNode.connect(outputAudioContext.destination);

            const sessionPromise = ai.live.connect({
                model: 'gemini-2.5-flash-native-audio-preview-09-2025',
                callbacks: {
                    onopen: async () => {
                        set({ isConnecting: false, isConnected: true });
                        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                        const source = inputAudioContext!.createMediaStreamSource(stream);
                        scriptProcessor = inputAudioContext!.createScriptProcessor(4096, 1, 1);
                        scriptProcessor.onaudioprocess = (audioProcessingEvent) => {
                            const inputData = audioProcessingEvent.inputBuffer.getChannelData(0);
                            const pcmBlob = createBlob(inputData);
                            sessionPromise.then((session) => {
                                session.sendRealtimeInput({ media: pcmBlob });
                            });
                        };
                        source.connect(scriptProcessor);
                        scriptProcessor.connect(inputAudioContext!.destination);
                    },
                    onmessage: async (message: LiveServerMessage) => {
                        // Handle audio output
                        const base64Audio = message.serverContent?.modelTurn?.parts[0]?.inlineData?.data;
                        if (base64Audio && outputAudioContext) {
                            nextStartTime = Math.max(nextStartTime, outputAudioContext.currentTime);
                            const audioBuffer = await decodeAudioData(decode(base64Audio), outputAudioContext, 24000, 1);
                            const sourceNode = outputAudioContext.createBufferSource();
                            sourceNode.buffer = audioBuffer;
                            sourceNode.connect(outputNode);
                            sourceNode.addEventListener('ended', () => sources.delete(sourceNode));
                            sourceNode.start(nextStartTime);
                            nextStartTime += audioBuffer.duration;
                            sources.add(sourceNode);
                        }

                        // Handle transcriptions
                        if (message.serverContent?.inputTranscription) {
                            set({ currentInputTranscription: message.serverContent.inputTranscription.text });
                        }
                        if (message.serverContent?.outputTranscription) {
                            set({ currentOutputTranscription: message.serverContent.outputTranscription.text });
                        }

                        // Handle turn completion
                        if (message.serverContent?.turnComplete) {
                            const { currentInputTranscription, currentOutputTranscription } = get();
                            const historyUpdates = [];
                            if (currentInputTranscription) {
                                historyUpdates.push({ id: generateId(), speaker: 'user' as const, text: currentInputTranscription });
                            }
                            if (currentOutputTranscription) {
                                historyUpdates.push({ id: generateId(), speaker: 'model' as const, text: currentOutputTranscription });
                            }
                            if(historyUpdates.length > 0) {
                                set(state => ({
                                    transcriptionHistory: [...state.transcriptionHistory, ...historyUpdates],
                                    currentInputTranscription: '',
                                    currentOutputTranscription: '',
                                }));
                            }
                        }
                         if (message.serverContent?.interrupted) {
                            for (const source of sources.values()) {
                                source.stop();
                                sources.delete(source);
                            }
                            nextStartTime = 0;
                        }
                    },
                    onerror: (e: ErrorEvent) => {
                        console.error('Live session error:', e);
                        get().addNotification({ type: 'error', message: 'Error en la conexión en tiempo real.' });
                        get().disconnectFromLive();
                    },
                    onclose: () => {
                        get().disconnectFromLive();
                    },
                },
                config: {
                    responseModalities: [Modality.AUDIO],
                    inputAudioTranscription: {},
                    outputAudioTranscription: {},
                },
            });
            set({ session: await sessionPromise });

        } catch (error) {
            console.error('Failed to connect to Live session:', error);
            get().addNotification({ type: 'error', message: 'No se pudo iniciar la sesión en tiempo real. ¿Permiso de micrófono denegado?' });
            get().disconnectFromLive(); // Ensure cleanup on failure
        }
    },
    
    disconnectFromLive: () => {
        const { session, isConnected } = get();
        if (!isConnected && !get().isConnecting) return;

        try {
            session?.close();
        } catch (e) {
            console.error("Error closing session:", e);
        }
        
        scriptProcessor?.disconnect();
        scriptProcessor = null;
        
        stream?.getTracks().forEach(track => track.stop());
        stream = null;

        inputAudioContext?.close().catch(console.error);
        outputAudioContext?.close().catch(console.error);
        inputAudioContext = null;
        outputAudioContext = null;

        sources.forEach(s => s.stop());
        sources.clear();
        nextStartTime = 0;

        set({
            isConnecting: false,
            isConnected: false,
            session: null,
            currentInputTranscription: '',
            currentOutputTranscription: '',
        });
    },
});