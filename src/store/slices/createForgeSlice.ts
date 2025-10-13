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
      logs: [],
    };
    set((state) => ({ trainingJobs: [newJob, ...state.trainingJobs] }));

    const { addTrainingLog, updateTrainingJobStatus } = get();

    // Simulate training process
    setTimeout(() => {
      updateTrainingJobStatus(newJob.id, 'TRAINING');
      addTrainingLog(newJob.id, 'Iniciando trabajo de entrenamiento...');
      
      const trainingSteps = [
        { delay: 1500, message: `Preparando dataset desde ${get().entities.filter(e => e.status === 'INTEGRATED').length} entidades.` },
        { delay: 3000, message: 'Dataset procesado. Iniciando fine-tuning del modelo base.' },
        { delay: 4500, message: 'Época de entrenamiento 1/3 completada. Pérdida: 0.123' },
        { delay: 6000, message: 'Época de entrenamiento 2/3 completada. Pérdida: 0.098' },
        { delay: 7500, message: 'Época de entrenamiento 3/3 completada. Pérdida: 0.072' },
        { delay: 8500, message: 'Modelo entrenado. Guardando artefactos...' },
      ];
      
      let cumulativeDelay = 0;
      trainingSteps.forEach(step => {
        cumulativeDelay += step.delay;
        setTimeout(() => addTrainingLog(newJob.id, step.message), cumulativeDelay);
      });

      setTimeout(() => {
        const success = Math.random() > 0.15; // 85% success rate
        if (success) {
            addTrainingLog(newJob.id, '¡Fine-tuning completado con éxito!');
            updateTrainingJobStatus(newJob.id, 'COMPLETED');
        } else {
            addTrainingLog(newJob.id, '¡ERROR! El entrenamiento ha fallado debido a un sobreajuste del modelo.');
            updateTrainingJobStatus(newJob.id, 'FAILED');
        }
      }, cumulativeDelay + 1000);

    }, 2000); // 2s queue time
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
});