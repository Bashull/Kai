import { ForgeSlice, AppSlice, TrainingJob, TrainingJobStatus } from '../../types';
import { apiClient } from '../../services/apiClient';

export const createForgeSlice: AppSlice<ForgeSlice> = (set, get) => ({
  trainingJobs: [],
  addTrainingJob: async (job) => {
    try {
      const response = await apiClient.startTraining(job);
      const newJob: TrainingJob = {
        ...job,
        id: response.jobId,
        status: 'QUEUED',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        logs: [{ timestamp: new Date().toISOString(), message: response.message }],
      };
      set((state) => ({ trainingJobs: [newJob, ...state.trainingJobs] }));
    } catch (error) {
      console.error("Failed to start training job:", error);
      get().addNotification({ type: 'error', message: 'Failed to start training job.' });
    }
  },
  updateTrainingJobStatus: (jobId, status) =>
    set((state) => {
      const trainingJobs = state.trainingJobs.map((j) =>
        j.id === jobId ? { ...j, status, updatedAt: new Date().toISOString() } : j
      );
      if (status === 'COMPLETED') {
        const job = state.trainingJobs.find(j => j.id === jobId);
        if (job) {
          get().addDiaryEntry({
            type: 'FORGE',
            content: `Fine-tuning completado para el modelo ${job.modelName}.`
          });
        }
      }
      return { trainingJobs };
    }),
  addTrainingLog: (jobId, message) => {
      set(state => ({
        trainingJobs: state.trainingJobs.map(job => 
            job.id === jobId ? { ...job, logs: [...(job.logs || []), { timestamp: new Date().toISOString(), message }] } : job
        )
      }))
  },
  pollJobs: async () => {
    const { trainingJobs } = get();
    const activeJobs = trainingJobs.filter(j => j.status === 'QUEUED' || j.status === 'TRAINING');
    
    if (activeJobs.length === 0) return;

    await Promise.all(activeJobs.map(async (job) => {
        try {
            const update = await apiClient.getTrainingJobStatus({ jobId: job.id });
            
            // This is a basic update. A real implementation might need more sophisticated logic
            // to handle log merging and prevent duplicate updates.
            set(state => ({
                trainingJobs: state.trainingJobs.map(j => {
                    if (j.id === job.id) {
                        // Avoid overwriting logs if the poll response doesn't contain any new ones
                        const newLogs = update.logs && update.logs.length > (j.logs?.length || 0) ? update.logs : j.logs;
                        return { ...j, status: update.status, logs: newLogs };
                    }
                    return j;
                })
            }));

        } catch (error) {
            console.error(`Failed to poll status for job ${job.id}:`, error);
            // Optionally update job status to FAILED on repeated poll errors
        }
    }));
  },
});