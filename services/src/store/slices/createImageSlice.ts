import { ImageSlice, AppSlice, GeneratedImage } from '../../types';

export const createImageSlice: AppSlice<ImageSlice> = (set) => ({
  imagePrompt: '',
  generatedImages: [],
  isGeneratingImages: false,
  setImagePrompt: (prompt: string) => set({ imagePrompt: prompt }),
  setGeneratedImages: (images: GeneratedImage[]) => set({ generatedImages: images }),
  setIsGeneratingImages: (isGenerating: boolean) => set({ isGeneratingImages: isGenerating }),
});
