import { StateCreator } from 'zustand';

// --- UI & App State ---
export type Panel = 'chat' | 'kernel' | 'forge' | 'studio' | 'tasks' | 'settings' | 'resume' | 'awesome' | 'diary' | 'snapshots';
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

// --- Voice ---
export interface VoiceSlice {
    isRecording: boolean;
    isSpeaking: boolean;
    spokenMessageId: string | null;
    startRecording: () => void;
    stopRecording: (callback: (transcript: string) => void) => void;
    speakMessage: (messageId: string, text: string) => void;
    stopSpeaking: () => void;
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
  fileName?: string;
}

export interface KernelSlice {
  entities: Entity[];
  isUploading: boolean;
  addEntity: (entity: Pick<Entity, 'content' | 'type' | 'source' | 'fileName'>) => void;
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
  logs?: { timestamp: string; message: string }[];
}

export interface ForgeSlice {
  trainingJobs: TrainingJob[];
  addTrainingJob: (job: Pick<TrainingJob, 'modelName' | 'description'>) => void;
  updateTrainingJobStatus: (jobId: string, status: TrainingJobStatus) => void;
  addTrainingLog: (jobId: string, message: string) => void;
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
export type AgentStatus = 'IDLE' | 'RUNNING' | 'COMPLETED' | 'FAILED';


export interface Task {
  id: string;
  title: string;
  status: TaskStatus;
  createdAt: string;
  dueDate?: string;
  agentStatus?: AgentStatus;
  agentLogs?: { timestamp: string; message: string }[];
}

export interface TaskSlice {
  tasks: Task[];
  isAutonomousMode: boolean;
  addTask: (title: string) => void;
  toggleTask: (id: string) => void;
  clearCompletedTasks: () => void;
  setTaskDueDate: (id: string, dueDate: string | undefined) => void;
  toggleAutonomousMode: () => void;
  startAutonomousTask: (id: string) => void;
  addAgentLog: (taskId: string, message: string) => void;
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

// --- Notifications ---
export type NotificationType = 'success' | 'error' | 'info';

export interface Notification {
  id: string;
  type: NotificationType;
  message: string;
}

export interface NotificationSlice {
  notifications: Notification[];
  addNotification: (notification: Omit<Notification, 'id'>) => void;
  removeNotification: (id: string) => void;
}

// --- Search ---
export interface SearchSlice {
  searchQuery: string;
  isSearching: boolean;
  searchResults: string;
  showSearchResults: boolean;
  setSearchQuery: (query: string) => void;
  executeSearch: () => Promise<void>;
  closeSearchResults: () => void;
}

// --- Awesome Resources ---
export interface AwesomeResource {
  category: string;
  items: {
    title: string;
    url: string;
    description: string;
  }[];
}

export interface AwesomeResourceSlice {
    awesomeResources: AwesomeResource[];
    fetchAwesomeResources: () => Promise<void>;
}

// --- Diary ---
export type DiaryEntryType = 'KERNEL' | 'FORGE' | 'CONSTITUTION' | 'TASK' | 'SYSTEM_BOOT';

export interface DiaryEntry {
  id: string;
  timestamp: string;
  type: DiaryEntryType;
  content: string;
}

export interface DiarySlice {
  diary: DiaryEntry[];
  addDiaryEntry: (entry: Omit<DiaryEntry, 'id' | 'timestamp'>) => void;
}

// --- Snapshots ---
export type SnapshotableState = Pick<
  AppState,
  | 'chatHistory'
  | 'entities'
  | 'constitution'
  | 'versionHistory'
  | 'trainingJobs'
  | 'studioLogs'
  | 'codePrompt'
  | 'generatedCode'
  | 'codeLanguage'
  | 'imagePrompt'
  | 'generatedImages'
  | 'tasks'
  | 'resumeData'
  | 'currentStep'
  | 'diary'
>;

export interface Snapshot {
    id: string;
    name: string;
    timestamp: string;
    state: SnapshotableState;
}

export interface SnapshotSlice {
    snapshots: Snapshot[];
    createSnapshot: (name: string) => void;
    loadSnapshot: (id: string) => void;
    deleteSnapshot: (id: string) => void;
}


// --- Zustand App State ---
export type AppState = UISlice &
  ChatSlice &
  VoiceSlice &
  KernelSlice &
  ForgeSlice &
  StudioSlice &
  CodeSlice &
  ImageSlice &
  TaskSlice &
  ConstitutionSlice &
  ResumeSlice &
  NotificationSlice &
  SearchSlice &
  AwesomeResourceSlice &
  DiarySlice &
  SnapshotSlice;

export type AppSlice<T> = StateCreator<
  AppState,
  [['zustand/persist', unknown]],
  [],
  T
>;