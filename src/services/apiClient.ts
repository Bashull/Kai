const API_BASE_URL = 'https://db7b1716-8580-4438-b2e5-26a39bc47d79-00-1v1sjqe5urhuq.spock.replit.dev';

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
    // In a real scenario, this would POST to a /api/forge/start-training endpoint
    console.log("Simulating startTraining API call with:", jobData);
    // Simulate a successful response with a job ID
    return Promise.resolve({
      jobId: `job_${Date.now()}`,
      status: 'QUEUED',
      message: 'Training job successfully queued.'
    });
  },
  getTrainingJobStatus: async ({ jobId }: { jobId: string }) => {
    // In a real scenario, this would GET from /api/forge/jobs/{jobId}
    console.log(`Simulating getTrainingJobStatus API call for job: ${jobId}`);
    // This is a mock response. A real backend would manage the state transitions.
    // For now, we'll just return a placeholder or you could add complex mock logic here.
     return Promise.resolve({
      jobId: jobId,
      status: 'TRAINING', // Mock: assume it's always training for polling demo
      logs: [{ timestamp: new Date().toISOString(), message: 'Polling status...' }],
    });
  },
};