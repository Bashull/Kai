import { StateCreator } from 'zustand';

// --- Tasks (Missions) ---
export interface Task {
  id: string;
  title: string;
  status: 'PENDING' | 'COMPLETED';
  createdAt: string;
  dueDate?: string;
  agentStatus?: 'IDLE' | 'RUNNING' | 'COMPLETED';
  agentLogs?: { timestamp: string; message: string }[];
}

// --- UI & App State ---
// FIX: Add 'avatars' to Panel type to support the new AvatarsPanel.
// FIX: Added 'video' and 'analysis' to Panel type to support the new panels.
export type Panel = 'chat' | 'live' | 'kernel' | 'forge' | 'studio' | 'tasks' | 'settings' | 'resume' | 'awesome' | 'diary' | 'snapshots' | 'evolution' | 'avatars' | 'video' | 'analysis';
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
  sources?: { uri: string; title: string }[];
}

export interface ChatSlice {
  isTyping: boolean;
  chatHistory: ChatMessage[];
  isSummarizing: boolean;
  thinkingMode: boolean;
  grounding: 'none' | 'web' | 'maps';
  addChatMessage: (message: Pick<ChatMessage, 'role' | 'content'> & { sources?: ChatMessage['sources'] }) => void;
  updateLastChatMessage: (content: string, sources?: ChatMessage['sources']) => void;
  setTyping: (isTyping: boolean) => void;
  summarizeAndSaveChat: () => Promise<void>;
  toggleThinkingMode: () => void;
  setGrounding: (grounding: 'none' | 'web' | 'maps') => void;
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

// --- Live Conversation ---
export interface LiveTranscriptionEntry {
  id: string;
  speaker: 'user' | 'model';
  text: string;
}

export interface LiveSlice {
  isConnecting: boolean;
  isConnected: boolean;
  session: any | null;
  analyserNode: AnalyserNode | null;
  transcriptionHistory: LiveTranscriptionEntry[];
  currentInputTranscription: string;
  currentOutputTranscription: string;
  connectToLive: () => Promise<void>;
  disconnectFromLive: () => void;
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
  addEntity: (entity: Pick<Entity, 'content' | 'type' | 'source'> & { fileName?: string }) => void;
  updateEntityStatus: (entityId: string, status: EntityStatus) => void;
}

// --- Forge (Fine-tuning) ---
export type TrainingJobStatus = 'QUEUED' | 'TRAINING' | 'COMPLETED' | 'FAILED';

export interface TrainingJob {
  id: string;
  modelName: string;
  description: string;
  datasetEntityIds?: string[];
  status: TrainingJobStatus;
  createdAt: string;
  updatedAt: string;
  logs?: { timestamp: string; message: string }[];
}

export interface ForgeSlice {
  trainingJobs: TrainingJob[];
  addTrainingJob: (job: Pick<TrainingJob, 'modelName' | 'description' | 'datasetEntityIds'>) => Promise<void>;
  updateTrainingJobStatus: (jobId: string, status: TrainingJobStatus) => void;
  addTrainingLog: (jobId: string, message: string) => void;
  pollJobs: () => Promise<void>;
}

// --- Studio (Code, Image, Console, Video, Analysis) ---
export type CodeLanguage = 'javascript' | 'typescript' | 'python' | 'html' | 'css' | 'json' | 'markdown';

export interface GeneratedImage {
  prompt: string;
  url: string;
}

export interface StudioLog {
    id: string;
    timestamp: string;
    type: 'COMMAND' | 'RESPONSE' | 'ERROR' | 'INFO';
    content: string;
}

export interface StudioSlice {
    isChecking: boolean;
    studioLogs: StudioLog[];
    setIsChecking: (isChecking: boolean) => void;
    addStudioLog: (log: Omit<StudioLog, 'id' | 'timestamp'>) => void;
    clearStudioLogs: () => void;
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

export type AspectRatio = "1:1" | "3:4" | "4:3" | "9:16" | "16:9";

export interface ImageSlice {
    imagePrompt: string;
    generatedImages: GeneratedImage[];
    isGeneratingImages: boolean;
    // FIX: Renamed to avoid conflict with VideoSlice
    imageAspectRatio: AspectRatio;
    setImagePrompt: (prompt: string) => void;
    setGeneratedImages: (images: GeneratedImage[]) => void;
    setIsGeneratingImages: (isGenerating: boolean) => void;
    // FIX: Renamed setter for consistency
    setImageAspectRatio: (ratio: AspectRatio) => void;
}

export interface VideoSlice {
  videoPrompt: string;
  inputImage: string | null; // base64
  // FIX: Renamed to avoid conflict with ImageSlice
  videoAspectRatio: '16:9' | '9:16';
  isGeneratingVideo: boolean;
  videoGenerationProgress: string;
  generatedVideoUrl: string | null;
  setVideoPrompt: (prompt: string) => void;
  setInputImage: (image: string | null) => void;
  setVideoAspectRatio: (ratio: '16:9' | '9:16') => void;
  generateVideo: () => Promise<void>;
}

export interface AnalysisSlice {
  analysisImage: string | null; // base64
  analysisPrompt: string;
  isAnalyzing: boolean;
  analysisResult: string;
  isEditing: boolean;
  editedImage: string | null;
  setAnalysisImage: (image: string | null) => void;
  setAnalysisPrompt: (prompt: string) => void;
  analyzeImage: () => Promise<void>;
  editImage: () => Promise<void>;
}


// --- TaskSlice Definition ---
export interface TaskSlice {
  tasks: Task[];
  isAutonomousMode: boolean;
  addTask: (title: string) => void;
  toggleTask: (id: string) => void;
  clearCompletedTasks: () => void;
  setTaskDueDate: (id: string, dueDate?: string) => void;
  toggleAutonomousMode: () => void;
  addAgentLog: (taskId: string, message: string) => void;
  startAutonomousTask: (id: string) => void;
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
export interface Notification {
  id: string;
  type: 'success' | 'error' | 'info';
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
    description: string;
    url: string;
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
export interface SnapshotableState {
    chatHistory: ChatMessage[];
    entities: Entity[];
    constitution: Constitution;
    versionHistory: ConstitutionVersion[];
    trainingJobs: TrainingJob[];
    studioLogs: StudioLog[];
    codePrompt: string;
    generatedCode: string;
    codeLanguage: CodeLanguage;
    imagePrompt: string;
    generatedImages: GeneratedImage[];
    tasks: Task[];
    resumeData: ResumeData;
    currentStep: number;
    diary: DiaryEntry[];
}

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

// --- Evolution ---
export interface EvolutionLog {
  id: string;
  timestamp: string;
  message: string;
}

export interface EvolutionSlice {
  isExtracting: boolean;
  extractionLogs: EvolutionLog[];
  runExtractionCycle: () => void;
}


// --- Main App State & Slice Creator ---
export interface AppState extends
    UISlice,
    ChatSlice,
    VoiceSlice,
    LiveSlice,
    KernelSlice,
    ForgeSlice,
    StudioSlice,
    CodeSlice,
    ImageSlice,
    VideoSlice,
    AnalysisSlice,
    TaskSlice,
    ConstitutionSlice,
    ResumeSlice,
    NotificationSlice,
    SearchSlice,
    AwesomeResourceSlice,
    DiarySlice,
    SnapshotSlice,
    EvolutionSlice {}

export type AppSlice<T> = StateCreator<AppState, [['zustand/persist', unknown]], [], T>;