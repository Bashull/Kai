// FIX: Replaced aliased import path with a relative path.
import { StudioSlice, AppSlice } from '../../types';
// FIX: Replaced aliased import path with a relative path.
import { generateId } from '../../utils/helpers';

export const createStudioSlice: AppSlice<StudioSlice> = (set) => ({
    isChecking: false,
    studioLogs: [],
    setIsChecking: (isChecking: boolean) => set({ isChecking }),
    addStudioLog: (log) => set(state => ({
        studioLogs: [...state.studioLogs, {
            ...log,
            id: generateId(),
            timestamp: new Date().toISOString(),
        }]
    })),
    clearStudioLogs: () => set({ studioLogs: [] }),
});