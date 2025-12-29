import { VoiceSlice, AppSlice } from '../../types';
import { generateSpeech } from '../../services/geminiService';
import { decode, decodeAudioData } from '../../utils/helpers';

// Browser SpeechRecognition for input
declare global {
  interface Window { SpeechRecognition: any; webkitSpeechRecognition: any; }
}

let recognition: any | null = null;
if (typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition)) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.lang = 'es-ES';
  recognition.interimResults = false;
}

// Web Audio API for output
let outputAudioContext: AudioContext | null = null;
let outputNode: GainNode | null = null;
let currentSource: AudioBufferSourceNode | null = null;

const initializeAudioContext = () => {
    if (!outputAudioContext) {
        outputAudioContext = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
        outputNode = outputAudioContext.createGain();
        outputNode.connect(outputAudioContext.destination);
    }
};

export const createVoiceSlice: AppSlice<VoiceSlice> = (set, get) => ({
  isRecording: false,
  isSpeaking: false,
  spokenMessageId: null,

  startRecording: () => {
    if (recognition && !get().isRecording) {
      recognition.start();
      set({ isRecording: true });
    } else {
        get().addNotification({ type: 'error', message: 'El reconocimiento de voz no es compatible con este navegador.' });
    }
  },

  stopRecording: (callback) => {
    if (recognition && get().isRecording) {
      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        callback(transcript);
        recognition.onresult = null;
      };
      recognition.stop();
      set({ isRecording: false });
    }
  },

  speakMessage: async (messageId, text) => {
    get().stopSpeaking();
    set({ isSpeaking: true, spokenMessageId: messageId });

    try {
      initializeAudioContext();
      const base64Audio = await generateSpeech(text);
      const audioBuffer = await decodeAudioData(decode(base64Audio), outputAudioContext!, 24000, 1);

      // If another speech was requested while we were generating, don't play this one.
      if (get().spokenMessageId !== messageId) return;

      currentSource = outputAudioContext!.createBufferSource();
      currentSource.buffer = audioBuffer;
      currentSource.connect(outputNode!);
      currentSource.onended = () => {
        // Check if this was the message that was supposed to be playing
        if (get().spokenMessageId === messageId) {
          set({ isSpeaking: false, spokenMessageId: null });
        }
        currentSource = null;
      };
      currentSource.start();
    } catch (error) {
      console.error("Failed to speak message:", error);
      get().addNotification({ type: 'error', message: 'No se pudo reproducir la respuesta de voz.' });
      set({ isSpeaking: false, spokenMessageId: null });
    }
  },

  stopSpeaking: () => {
    if (currentSource) {
      currentSource.onended = null; // Prevent onended from firing when manually stopped
      currentSource.stop();
      currentSource = null;
    }
    set({ isSpeaking: false, spokenMessageId: null });
  },
});
