import { AppSlice, AnalysisSlice } from '../../types';
import { analyzeImage as analyzeImageAPI, editImage as editImageAPI } from '../../services/geminiService';

export const createAnalysisSlice: AppSlice<AnalysisSlice> = (set, get) => ({
  analysisImage: null,
  analysisPrompt: '',
  isAnalyzing: false,
  analysisResult: '',
  isEditing: false,
  editedImage: null,
  setAnalysisImage: (image) => set({ analysisImage: image, analysisResult: '', editedImage: null }),
  setAnalysisPrompt: (prompt) => set({ analysisPrompt: prompt }),
  analyzeImage: async () => {
    const { analysisImage, analysisPrompt } = get();
    if (!analysisImage) {
      get().addNotification({ type: 'info', message: 'Por favor, sube una imagen para analizar.' });
      return;
    }
    set({ isAnalyzing: true, analysisResult: '' });
    try {
      const result = await analyzeImageAPI(analysisImage, analysisPrompt || "Describe esta imagen en detalle.");
      set({ analysisResult: result });
    } catch (error) {
      console.error("Image analysis failed:", error);
      const errorMessage = error instanceof Error ? error.message : "Error desconocido";
      set({ analysisResult: `**Error:** ${errorMessage}` });
      get().addNotification({ type: 'error', message: 'El análisis de la imagen falló.' });
    } finally {
      set({ isAnalyzing: false });
    }
  },
  editImage: async () => {
    const { analysisImage, analysisPrompt } = get();
    if (!analysisImage || !analysisPrompt) {
      get().addNotification({ type: 'info', message: 'Sube una imagen y escribe un prompt de edición.' });
      return;
    }
    set({ isEditing: true, editedImage: null });
    try {
      const result = await editImageAPI(analysisImage, analysisPrompt);
      set({ editedImage: result });
    } catch (error) {
      console.error("Image editing failed:", error);
      const errorMessage = error instanceof Error ? error.message : "Error desconocido";
      get().addNotification({ type: 'error', message: `La edición de imagen falló: ${errorMessage}` });
    } finally {
      set({ isEditing: false });
    }
  },
});