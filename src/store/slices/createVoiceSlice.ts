import { VoiceSlice, AppSlice } from '../../types';

// Declare SpeechRecognition interfaces for cross-browser compatibility
declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

let recognition: any | null = null;
if (typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition)) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.lang = 'es-ES';
  recognition.interimResults = false;
}

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
        recognition.onresult = null; // Clean up
      };
      recognition.stop();
      set({ isRecording: false });
    }
  },

  speakMessage: (messageId, text) => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      get().stopSpeaking(); // Stop any currently playing speech
      
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'es-ES';
      utterance.rate = 1.0;
      utterance.pitch = 1.0;

      utterance.onstart = () => {
        set({ isSpeaking: true, spokenMessageId: messageId });
      };

      utterance.onend = () => {
        set({ isSpeaking: false, spokenMessageId: null });
      };
      
      utterance.onerror = () => {
         set({ isSpeaking: false, spokenMessageId: null });
      }

      window.speechSynthesis.speak(utterance);
    } else {
         get().addNotification({ type: 'error', message: 'La síntesis de voz no es compatible con este navegador.' });
    }
  },

  stopSpeaking: () => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      set({ isSpeaking: false, spokenMessageId: null });
    }
  },
});