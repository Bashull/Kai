import { AppSlice, SearchSlice } from '../../types';
// FIX: Corrected import path for geminiService.
import { performAISearch } from '../../../src/services/geminiService';

export const createSearchSlice: AppSlice<SearchSlice> = (set, get) => ({
  searchQuery: '',
  isSearching: false,
  searchResults: '',
  showSearchResults: false,
  setSearchQuery: (query: string) => set({ searchQuery: query }),
  executeSearch: async () => {
    const { searchQuery, entities } = get();
    if (!searchQuery.trim()) return;

    set({ isSearching: true, showSearchResults: true, searchResults: '' });

    try {
      const results = await performAISearch(searchQuery, entities);
      set({ searchResults: results });
    } catch (error) {
      console.error("AI Search failed:", error);
      const errorMessage = error instanceof Error ? error.message : "An unknown error occurred.";
      set({ searchResults: `**Error durante la búsqueda:**\n\n${errorMessage}` });
    } finally {
      set({ isSearching: false });
    }
  },
  closeSearchResults: () => set({ showSearchResults: false, searchQuery: '' }),
});