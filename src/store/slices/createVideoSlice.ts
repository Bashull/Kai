import { AppSlice, VideoSlice } from '../../types';
import { generateVideo as generateVideoAPI } from '../../services/geminiService';

export const createVideoSlice: AppSlice<VideoSlice> = (set, get) => ({
  videoPrompt: '',
  inputImage: null,
  // FIX: Renamed property to avoid type conflict
  videoAspectRatio: '16:9',
  isGeneratingVideo: false,
  videoGenerationProgress: '',
  generatedVideoUrl: null,
  setVideoPrompt: (prompt) => set({ videoPrompt: prompt }),
  setInputImage: (image) => set({ inputImage: image }),
  setVideoAspectRatio: (ratio) => set({ videoAspectRatio: ratio }),
  generateVideo: async () => {
    // FIX: Use the renamed state property
    const { videoPrompt, inputImage, videoAspectRatio } = get();
    if (!videoPrompt.trim() && !inputImage) {
      get().addNotification({ type: 'info', message: 'Se requiere un prompt de texto o una imagen de entrada.' });
      return;
    }

    set({ isGeneratingVideo: true, generatedVideoUrl: null, videoGenerationProgress: 'Iniciando la generación de vídeo...' });

    try {
      // The API service will handle polling and progress updates via callback
      const videoUrl = await generateVideoAPI({
        prompt: videoPrompt,
        image: inputImage ? { imageBytes: inputImage, mimeType: 'image/png' } : undefined,
        config: {
          // FIX: Pass the renamed variable to the API call
          aspectRatio: videoAspectRatio,
          resolution: '720p',
          numberOfVideos: 1,
        },
        onProgress: (progressMessage) => {
          set({ videoGenerationProgress: progressMessage });
        }
      });
      
      set({ generatedVideoUrl: videoUrl, videoGenerationProgress: '¡Vídeo generado con éxito!' });
      get().addNotification({ type: 'success', message: 'El vídeo se ha generado correctamente.' });
    } catch (error) {
      console.error("Video generation failed:", error);
      const errorMessage = error instanceof Error ? error.message : "Error desconocido";
      set({ videoGenerationProgress: `Error: ${errorMessage}` });
      get().addNotification({ type: 'error', message: `La generación de vídeo falló: ${errorMessage}` });
    } finally {
      set({ isGeneratingVideo: false });
    }
  },
});