import { StateCreator } from 'zustand';

// --- UI & App State ---
export type Panel = 'chat' | 'kernel' | 'forge' | 'studio' | 'tasks' | 'settings' | 'resume';
export type Theme = 'light' | 'dark';

export interface UISlice {
  activePanel: Panel;
  sidebarCollapsed: boolean;
  theme: Theme;
  dueTasks: Task[];
  showNotifications: boolean;
  setActivePanel: (panel: Panel) => void;
  toggleSidebar: () => void;
  setTheme: (theme: Theme) => void;
  setDueTasks: (tasks: Task[]) => void;
  toggleNotifications: () => void;
}

// --- Chat ---
export interface ChatMessage {
  id: string;
  timestamp: string;
  role: 'user' | 'model';
  content: string;
}

export interface ChatSlice {
  isTyping: boolean;
  chatHistory: ChatMessage[];
  addChatMessage: (message: Pick<ChatMessage, 'role' | 'content'>) => void;
  updateLastChatMessage: (content: string) => void;
  setTyping: (isTyping: boolean) => void;
}

// --- Kernel (Knowledge Base) ---
export type EntityType = 'TEXT' | 'URL' | 'DOCUMENT';
export type EntityStatus = 'ASSIMILATING' | 'INTEGRATED' | 'REJECTED';

export interface Entity {
  id: string;
  content: string;
  type: EntityType;
  source: string;
  status: EntityStatus;
  createdAt: string;
  updatedAt: string;
}

export interface KernelSlice {
  entities: Entity[];
  addEntity: (entity: Pick<Entity, 'content' | 'type' | 'source'>) => void;
  updateEntityStatus: (entityId: string, status: EntityStatus) => void;
}

// --- Constitution ---
export interface Constitution {
  masterDirective: string;
  principles: string[];
}
export interface ConstitutionVersion {
  version: number;
  date: string;
  constitution: Constitution;
}
export interface ConstitutionSlice {
  constitution: Constitution;
  versionHistory: ConstitutionVersion[];
  updateConstitution: (newConstitution: Constitution) => void;
  revertToVersion: (version: number) => void;
}


// --- Forge (Model Training) ---
export type TrainingJobStatus = 'QUEUED' | 'TRAINING' | 'COMPLETED' | 'FAILED';

export interface TrainingJob {
  id: string;
  modelName: string;
  description: string;
  status: TrainingJobStatus;
  createdAt: string;
  updatedAt: string;
}

export interface ForgeSlice {
  trainingJobs: TrainingJob[];
  addTrainingJob: (job: Pick<TrainingJob, 'modelName' | 'description'>) => void;
  updateTrainingJobStatus: (jobId: string, status: TrainingJobStatus) => void;
}

// --- Studio (Tools) ---
export type CodeLanguage = 'javascript' | 'typescript' | 'python' | 'html' | 'css' | 'json' | 'markdown';

export interface GeneratedImage {
  url: string;
  prompt: string;
}

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

export interface ImageSlice {
    imagePrompt: string;
    generatedImages: GeneratedImage[];
    isGeneratingImages: boolean;
    setImagePrompt: (prompt: string) => void;
    setGeneratedImages: (images: GeneratedImage[]) => void;
    setIsGeneratingImages: (isGenerating: boolean) => void;
}

export type StudioLogType = 'COMMAND' | 'RESPONSE' | 'ERROR' | 'INFO';

export interface StudioLog {
    id: string;
    timestamp: string;
    type: StudioLogType;
    content: string;
}

export interface StudioSlice {
    isChecking: boolean;
    studioLogs: StudioLog[];
    setIsChecking: (isChecking: boolean) => void;
    addStudioLog: (log: Omit<StudioLog, 'id' | 'timestamp'>) => void;
    clearStudioLogs: () => void;
}

// --- Tasks ---
export type TaskStatus = 'PENDING' | 'COMPLETED';

export interface Task {
  id: string;
  title: string;
  status: TaskStatus;
  createdAt: string;
  dueDate?: string;
}

export interface TaskSlice {
  tasks: Task[];
  addTask: (title: string) => void;
  toggleTask: (id: string) => void;
  clearCompletedTasks: () => void;
  setTaskDueDate: (id: string, dueDate: string | undefined) => void;
}

// --- Resume Builder ---
export interface PersonalInfo {
  fullName: string;
  email: string;
  phoneNumber: string;
  address: string;
  website: string;
}

export interface Experience {
  id: string;
  jobTitle: string;
  company: string;
  location: string;
  startDate: string;
  endDate: string;
  isCurrent: boolean;
  description: string;
}

export interface Education {
  id: string;
  institution: string;
  degree: string;
  fieldOfStudy: string;
  startDate: string;
  endDate: string;
}

export interface Skill {
  id: string;
  name: string;
}

export interface ResumeData {
  personalInfo: PersonalInfo;
  experience: Experience[];
  education: Education[];
  skills: Skill[];
  summary: string;
}

export interface ResumeSlice {
  currentStep: number;
  resumeData: ResumeData;
  isGenerating: boolean;
  setCurrentStep: (step: number) => void;
  setResumeData: (data: Partial<ResumeData>) => void;
  updatePersonalInfo: (field: keyof PersonalInfo, value: string) => void;
  addExperience: () => void;
  updateExperience: (index: number, field: keyof Experience, value: string | boolean) => void;
  removeExperience: (id: string) => void;
  addEducation: () => void;
  updateEducation: (index: number, field: keyof Education, value: string) => void;
  removeEducation: (id: string) => void;
  addSkill: (name: string) => void;
  removeSkill: (id: string) => void;
  setSummary: (summary: string) => void;
  setIsGenerating: (isGenerating: boolean) => void;
}


// --- Zustand App State ---
export type AppState = UISlice &
  ChatSlice &
  KernelSlice &
  ForgeSlice &
  StudioSlice &
  CodeSlice &
  ImageSlice &
  TaskSlice &
  ConstitutionSlice &
  ResumeSlice;

export type AppSlice<T> = StateCreator<
  AppState,
  [['zustand/persist', unknown]],
  [],
  T
>;
