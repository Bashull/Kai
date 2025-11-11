import { StudioSlice, AppSlice } from '../../types';
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
