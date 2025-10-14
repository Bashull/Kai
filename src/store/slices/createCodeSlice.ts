// FIX: Replaced aliased import path with a relative path.
import { CodeSlice, AppSlice, CodeLanguage } from '../../types';

export const createCodeSlice: AppSlice<CodeSlice> = (set) => ({
  codePrompt: '',
  generatedCode: `// Bienvenido al Generador de Código de Kai.
// Describe el código que necesitas, elige un lenguaje y haz clic en "Generar".`,
  codeLanguage: 'javascript',
  isGeneratingCode: false,
  setCodePrompt: (prompt: string) => set({ codePrompt: prompt }),
  setGeneratedCode: (code: string) => set({ generatedCode: code }),
  setCodeLanguage: (language: CodeLanguage) => set({ codeLanguage: language }),
  setIsGeneratingCode: (isGenerating: boolean) => set({ isGeneratingCode: isGenerating }),
});