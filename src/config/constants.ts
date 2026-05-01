// AI Model identifiers
export const MODELS = {
  CHAT_FAST: 'gemini-2.5-flash',
  CHAT_PRO: 'gemini-2.5-pro',
  IMAGE_GEN: 'imagen-4.0-generate-001',
  IMAGE_EDIT: 'gemini-2.5-flash-image',
  VIDEO_GEN: 'veo-3.1-fast-generate-preview',
  TTS: 'gemini-2.5-flash-preview-tts',
  LIVE_AUDIO: 'gemini-2.5-flash-native-audio-preview-09-2025',
} as const;

// CHI homeostasis thresholds
export const CHI_THRESHOLDS = {
  COHERENCE_CRITICAL: 0.45,
  ENTROPY_CRITICAL: 0.82,
  ENTROPY_ALERT: 0.72,
  FATIGUE_ALERT: 0.68,
  ENERGY_ALERT: 0.35,
  COHERENCE_FOCUS: 0.82,
  ENTROPY_FOCUS: 0.35,
  FATIGUE_REST: 0.7,
  ENERGY_REST: 0.3,
} as const;

// CHI restoration deltas
export const CHI_RESTORE = {
  ENERGY: 0.12,
  COHERENCE: 0.18,
  ENTROPY: -0.16,
  FATIGUE: -0.14,
} as const;

// Timeouts (ms)
export const TIMEOUTS = {
  FETCH: 15_000,
  VIDEO_POLL_INTERVAL: 10_000,
  VIDEO_MAX_POLLS: 60,
  JOB_POLL_INTERVAL: 5_000,
  THINKING_BUDGET: 32768,
} as const;

// Storage limits to prevent localStorage overflow
export const STORAGE_LIMITS = {
  CHAT_HISTORY: 500,
  DIARY: 200,
  ENTITIES: 300,
  SNAPSHOTS: 50,
  TRAINING_JOBS: 100,
} as const;

// Input limits
export const INPUT_LIMITS = {
  CHAT_MAX_CHARS: 10_000,
} as const;
