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
};
