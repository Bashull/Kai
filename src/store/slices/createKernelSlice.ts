import { KernelSlice, AppSlice, Entity } from '../../types';
import { generateId } from '../../utils/helpers';

export const createKernelSlice: AppSlice<KernelSlice> = (set, get) => ({
  entities: [],
  addEntity: (entity) => {
    const newEntity: Entity = {
      ...entity,
      id: generateId(),
      status: 'ASSIMILATING',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    set((state) => ({ entities: [newEntity, ...state.entities] }));

    // Simulate assimilation process
    const assimilationTime = Math.random() * 4000 + 2000; // 2-6 seconds
    setTimeout(() => {
      const success = Math.random() > 0.1; // 90% success rate
      get().updateEntityStatus(newEntity.id, success ? 'INTEGRATED' : 'REJECTED');
    }, assimilationTime);
  },
  updateEntityStatus: (entityId, status) =>
    set((state) => ({
      entities: state.entities.map((e) =>
        e.id === entityId ? { ...e, status, updatedAt: new Date().toISOString() } : e
      ),
    })),
});
