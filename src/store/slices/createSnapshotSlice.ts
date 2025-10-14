import { AppSlice, SnapshotSlice, Snapshot, SnapshotableState } from '../../types';
import { generateId } from '../../utils/helpers';

const SNAPSHOTABLE_KEYS: (keyof SnapshotableState)[] = [
  'chatHistory', 'entities', 'constitution', 'versionHistory', 'trainingJobs', 'studioLogs',
  'codePrompt', 'generatedCode', 'codeLanguage', 'imagePrompt', 'generatedImages', 'tasks',
  'resumeData', 'currentStep', 'diary'
];

export const createSnapshotSlice: AppSlice<SnapshotSlice> = (set, get) => ({
  snapshots: [],
  createSnapshot: (name: string) => {
    const currentState = get();
    const stateToSave: Partial<SnapshotableState> = {};

    for (const key of SNAPSHOTABLE_KEYS) {
      (stateToSave as any)[key] = currentState[key];
    }

    const newSnapshot: Snapshot = {
      id: generateId(),
      name: name.trim() || `Snapshot ${new Date().toLocaleString()}`,
      timestamp: new Date().toISOString(),
      state: stateToSave as SnapshotableState,
    };

    set(state => ({ snapshots: [newSnapshot, ...state.snapshots] }));
    get().addNotification({ type: 'success', message: `Snapshot "${newSnapshot.name}" creado.` });
  },

  loadSnapshot: (id: string) => {
    const snapshot = get().snapshots.find(s => s.id === id);
    if (snapshot) {
      set(snapshot.state as any, true);
      set({ activePanel: 'chat', showSearchResults: false, showNotifications: false });
      get().addNotification({ type: 'info', message: `Snapshot "${snapshot.name}" cargado.` });
    } else {
      get().addNotification({ type: 'error', message: "No se pudo encontrar el snapshot." });
    }
  },

  deleteSnapshot: (id: string) => {
    const snapshotName = get().snapshots.find(s => s.id === id)?.name;
    set(state => ({
      snapshots: state.snapshots.filter(s => s.id !== id),
    }));
    if (snapshotName) {
        get().addNotification({ type: 'success', message: `Snapshot "${snapshotName}" eliminado.` });
    }
  },
});
