import { StateCreator } from 'zustand';

// General Types
export type Panel = 'chat' | 'kernel' | 'forge' | 'studio' | 'settings';
export type Theme = 'dark' | 'light';

// UI Slice
export interface UISlice {
  activePanel: Panel;
  sidebarCollapsed: boolean;
  theme: Theme;
  setActivePanel: (panel: Panel) => void;
  toggleSidebar: () => void;
  setTheme: (theme: Theme) => void;
}

// Chat Slice
export interface ChatMessage {
  id: string;
  role: 'user' | 'model';
  content: string;
  timestamp: string;
}
export interface ChatSlice {
  isTyping: boolean;
  chatHistory: ChatMessage[];
  addChatMessage: (message: Pick<ChatMessage, 'role' | 'content'>) => void;
  updateLastChatMessage: (content: string) => void;
  setTyping: (isTyping: boolean) => void;
}

// Kernel Slice
export type EntityStatus = 'ASSIMILATING' | 'INTEGRATED' | 'REJECTED';
export interface Entity {
  id: string;
  name: string;
  content: string;
  status: EntityStatus;
  createdAt: string;
  updatedAt: string;
}
export interface KernelSlice {
  entities: Entity[];
  addEntity: (entity: Pick<Entity, 'name' | 'content'>) => void;
  updateEntityStatus: (entityId: string, status: EntityStatus) => void;
}

// Forge Slice
export type TrainingJobStatus = 'QUEUED' | 'TRAINING' | 'COMPLETED' | 'FAILED';
export interface TrainingJob {
  id: string;
  modelName: string;
  status: TrainingJobStatus;
  createdAt: string;
  updatedAt: string;
  description: string;
}
export interface ForgeSlice {
  trainingJobs: TrainingJob[];
  addTrainingJob: (job: Pick<TrainingJob, 'modelName' | 'description'>) => void;
  updateTrainingJobStatus: (jobId: string, status: TrainingJobStatus) => void;
}

// Studio - Console Slice
export type LogType = 'COMMAND' | 'RESPONSE' | 'ERROR' | 'INFO';
export interface StudioLog {
    id: string;
    timestamp: string;
    type: LogType;
    content: string;
}
export interface StudioSlice {
    isChecking: boolean;
    studioLogs: StudioLog[];
    setIsChecking: (isChecking: boolean) => void;
    addStudioLog: (log: Omit<StudioLog, 'id' | 'timestamp'>) => void;
    clearStudioLogs: () => void;
}

// Studio - Code Slice
export type CodeLanguage =
  | 'javascript'
  | 'typescript'
  | 'python'
  | 'html'
  | 'css'
  | 'json'
  | 'markdown';

export interface CodeSlice {
  codePrompt: string;
  generatedCode: string;
  codeLanguage: CodeLanguage;
  isGeneratingCode: boolean;
  setCodePrompt: (prompt: string) => void;
  setGeneratedCode: (code: string) => void;
  setCodeLanguage: (language: CodeLanguage) => void;
  setIsGeneratingCode: (isGenerating: boolean) => void;
}

// Studio - Image Slice
export interface GeneratedImage {
    prompt: string;
    url: string;
}
export interface ImageSlice {
  imagePrompt: string;
  generatedImages: GeneratedImage[];
  isGeneratingImages: boolean;
  setImagePrompt: (prompt: string) => void;
  setGeneratedImages: (images: GeneratedImage[]) => void;
  setIsGeneratingImages: (isGenerating: boolean) => void;
}

// Combined App State
export type AppState = UISlice & ChatSlice & KernelSlice & ForgeSlice & StudioSlice & CodeSlice & ImageSlice;

// Type for Zustand slice creators
export type AppSlice<T> = StateCreator<
  AppState,
  [['zustand/persist', unknown]],
  [],
  T
>;

// FIX: Add missing types for Resume Builder
export interface PersonalInfo {
  fullName: string;
  email: string;
  phoneNumber: string;
  address: string;
}

export interface Experience {
  id: string;
  company: string;
  role: string;
  startDate: string;
  endDate: string;
  description: string;
}

export interface Education {
  id: string;
  institution: string;
  degree: string;
  startDate: string;
  endDate: string;
}

export type ResumeTemplate = 'classic' | 'modern';

export interface ResumeData {
  personalInfo: PersonalInfo;
  experience: Experience[];
  education: Education[];
  skills: string[];
  summary: string;
  template: ResumeTemplate;
  accentColor: string;
}

export interface ResumeStore extends ResumeData {
  currentStep: number;
  setPersonalInfo: (info: PersonalInfo) => void;
  addExperience: () => void;
  updateExperience: (index: number, field: keyof Omit<Experience, 'id'>, value: string) => void;
  removeExperience: (id: string) => void;
  addEducation: () => void;
  updateEducation: (index: number, field: keyof Omit<Education, 'id'>, value: string) => void;
  removeEducation: (id: string) => void;
  setSkills: (skills: string[]) => void;
  addSkill: (skill: string) => void;
  removeSkill: (index: number) => void;
  setSummary: (summary: string) => void;
  setTemplate: (template: ResumeTemplate) => void;
  setAccentColor: (color: string) => void;
  nextStep: () => void;
  prevStep: () => void;
}