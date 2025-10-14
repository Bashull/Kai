import React from 'react';
import { useAppStore } from './src/store/useAppStore';
import { generateWithAI } from './src/services/geminiService';
import { AIButton } from './src/components/ui/AIButton';

const SummaryStep: React.FC = () => {
  // FIX: Correctly destructure `summary` from `resumeData`.
  const { resumeData, setSummary, setIsGenerating, addNotification } = useAppStore();
  const { summary } = resumeData;

  const handleAIGenerate = async () => {
    if (resumeData.experience.length === 0) {
      addNotification({ type: 'info', message: "Añade alguna experiencia laboral para que pueda generar un resumen." });
      return;
    }
    setIsGenerating(true);
    const experienceText = resumeData.experience.map(e => `- ${e.jobTitle} at ${e.company}: ${e.description}`).join('\n');
    const skillsText = resumeData.skills.map(s => s.name).join(', ');
    const prompt = `Escribe un resumen profesional para un currículum basado en la siguiente información. Debe ser un párrafo de 3-4 frases que destaque los logros y habilidades clave. \n\nExperiencia:\n${experienceText}\n\nHabilidades:\n${skillsText}`;
    
    try {
      const result = await generateWithAI(prompt);
      setSummary(result);
    } catch (error) {
      console.error(error);
      addNotification({ type: 'error', message: "No se pudo generar el resumen." });
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-text-primary">Resumen Profesional</h2>
        <AIButton onClick={handleAIGenerate}>Generar con IA</AIButton>
      </div>
      <p className="text-text-secondary text-sm">Escribe un breve párrafo que destaque tu experiencia y tus objetivos profesionales.</p>
      <textarea
        value={summary}
        onChange={(e) => setSummary(e.target.value)}
        className="form-textarea w-full"
        rows={8}
        placeholder="Ej: Ingeniero de Software proactivo con 5 años de experiencia..."
      />
    </div>
  );
};

export default SummaryStep;