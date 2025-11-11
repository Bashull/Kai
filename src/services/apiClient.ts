import { TrainingJob } from '../types';

const API_BASE_URL = 'https://db7b1716-8580-4438-b2e5-26a39bc47d79-00-1v1sjqe5urhuq.spock.replit.dev';

// --- Stateful Mock for Forge Jobs ---
const mockJobs = new Map<string, TrainingJob>();

const MOCK_LOGS = [
  "Epoch 1/10 - loss: 1.234, accuracy: 0.65",
  "Epoch 2/10 - loss: 0.987, accuracy: 0.72",
  "Epoch 3/10 - loss: 0.765, accuracy: 0.78",
  "Epoch 4/10 - loss: 0.654, accuracy: 0.81",
  "Epoch 5/10 - loss: 0.543, accuracy: 0.85",
  "Epoch 6/10 - loss: 0.432, accuracy: 0.88",
  "Epoch 7/10 - loss: 0.321, accuracy: 0.91",
  "Epoch 8/10 - loss: 0.210, accuracy: 0.94",
  "Epoch 9/10 - loss: 0.150, accuracy: 0.96",
  "Epoch 10/10 - loss: 0.100, accuracy: 0.98",
  "Model training completed successfully.",
  "Saving model artifacts...",
];


async function handleResponse(response: Response) {
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API call failed with status ${response.status}: ${errorText}`);
  }
  return response.json();
}

export const apiClient: { [key: string]: (args: any) => Promise<any> } = {
  getMemories: async () => {
    const response = await fetch(`${API_BASE_URL}/api/consciousness/memories`);
    return handleResponse(response);
  },
  getDiary: async () => {
    const response = await fetch(`${API_BASE_URL}/api/consciousness/diary`);
    return handleResponse(response);
  },
  getSnapshots: async () => {
    const response = await fetch(`${API_BASE_URL}/api/consciousness/snapshots`);
    return handleResponse(response);
  },
  searchMemories: async ({ query }: { query: string }) => {
    const response = await fetch(`${API_BASE_URL}/api/consciousness/search?query=${encodeURIComponent(query)}`);
    return handleResponse(response);
  },
  compileMemory: async () => {
    const response = await fetch(`${API_BASE_URL}/api/consciousness/memory/compile`, {
        method: 'POST'
    });
    return handleResponse(response);
  },
  startTraining: async (jobData: { modelName: string; description: string }) => {
    console.log("Simulating startTraining API call with:", jobData);
    const jobId = `job_${Date.now()}`;
    const newJob: TrainingJob = {
      id: jobId,
      ...jobData,
      status: 'QUEUED',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      logs: [{ timestamp: new Date().toISOString(), message: 'Training job successfully queued.' }],
    };
    mockJobs.set(jobId, newJob);

    return Promise.resolve({
      jobId: jobId,
      status: 'QUEUED',
      message: 'Training job successfully queued.'
    });
  },
  getTrainingJobStatus: async ({ jobId }: { jobId: string }) => {
    console.log(`Simulating getTrainingJobStatus API call for job: ${jobId}`);
    const job = mockJobs.get(jobId);
    if (!job) {
      return Promise.reject(new Error(`Job with ID ${jobId} not found.`));
    }
    
    // Simulate state transitions and log generation
    const now = new Date();
    const lastUpdate = new Date(job.updatedAt);
    const timeDiff = now.getTime() - lastUpdate.getTime();

    // Only update every ~5 seconds to simulate polling
    if (timeDiff < 4000) {
      return Promise.resolve(job);
    }
    
    job.updatedAt = now.toISOString();

    switch (job.status) {
      case 'QUEUED':
        job.status = 'TRAINING';
        job.logs?.push({ timestamp: now.toISOString(), message: 'Starting training environment...' });
        break;
      case 'TRAINING':
        const currentLogCount = job.logs?.length || 0;
        if (currentLogCount -1 < MOCK_LOGS.length) {
          job.logs?.push({ timestamp: now.toISOString(), message: MOCK_LOGS[currentLogCount-1] });
        } else {
          job.status = Math.random() > 0.1 ? 'COMPLETED' : 'FAILED'; // 90% success rate
          job.logs?.push({ timestamp: now.toISOString(), message: job.status === 'COMPLETED' ? 'Job finished.' : 'Job failed due to an error.' });
        }
        break;
    }
    
    mockJobs.set(jobId, job);
    return Promise.resolve(job);
  },
};
