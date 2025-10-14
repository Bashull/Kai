// FIX: Replaced aliased import path with a relative path.
import { AwesomeResourceSlice, AppSlice } from '../../types';

export const createAwesomeResourceSlice: AppSlice<AwesomeResourceSlice> = (set) => ({
  awesomeResources: [],
  fetchAwesomeResources: async () => {
    try {
      const response = await fetch('/awesome.json');
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      const data = await response.json();
      set({ awesomeResources: data });
    } catch (error) {
      console.error("Failed to fetch awesome resources:", error);
      // You could set an error state here if needed
    }
  },
});