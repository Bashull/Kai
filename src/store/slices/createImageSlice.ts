import { ImageSlice, AppSlice, GeneratedImage, AspectRatio } from '../../types';

export const createImageSlice: AppSlice<ImageSlice> = (set) => ({
  imagePrompt: '',
  generatedImages: [],
  isGeneratingImages: false,
  imageAspectRatio: '1:1',
  setImagePrompt: (prompt: string) => set({ imagePrompt: prompt }),
  setGeneratedImages: (images: GeneratedImage[]) => set({ generatedImages: images }),
  setIsGeneratingImages: (isGenerating: boolean) => set({ isGeneratingImages: isGenerating }),
  setImageAspectRatio: (ratio: AspectRatio) => set({ imageAspectRatio: ratio }),
});
