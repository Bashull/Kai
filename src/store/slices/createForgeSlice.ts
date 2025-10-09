import { ForgeSlice, AppSlice, TrainingJob } from '../../types';
import { generateId } from '../../utils/helpers';

export const createForgeSlice: AppSlice<ForgeSlice> = (set, get) => ({
  trainingJobs: [],
  addTrainingJob: (job) => {
    const newJob: TrainingJob = {
      ...job,
      id: generateId(),
      status: 'QUEUED',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    set((state) => ({ trainingJobs: [newJob, ...state.trainingJobs] }));

    // Simulate training process
    setTimeout(() => {
      get().updateTrainingJobStatus(newJob.id, 'TRAINING');
      const trainingTime = Math.random() * 8000 + 5000; // 5-13 seconds
      setTimeout(() => {
        const success = Math.random() > 0.15; // 85% success rate
        get().updateTrainingJobStatus(newJob.id, success ? 'COMPLETED' : 'FAILED');
      }, trainingTime);
    }, 2000); // 2s queue time
  },
  updateTrainingJobStatus: (jobId, status) =>
    set((state) => ({
      trainingJobs: state.trainingJobs.map((j) =>
        j.id === jobId ? { ...j, status, updatedAt: new Date().toISOString() } : j
      ),
    })),
});
