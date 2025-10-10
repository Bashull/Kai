import React, { useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { generateWithAI } from '../../services/geminiService';
import { AIButton } from '../common';
import { X } from 'lucide-react';
import { motion } from 'framer-motion';

const SkillsStep: React.FC = () => {
  const { skills, addSkill, removeSkill, resumeData, setIsGenerating } = useAppStore();
  const [newSkill, setNewSkill] = useState('');

  const handleAddSkill = () => {
    addSkill(newSkill);
    setNewSkill('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      handleAddSkill();
    }
  };

  const handleAISuggestions = async () => {
      const jobTitles = resumeData.experience.map(e => e.jobTitle).join(', ');
      if (!jobTitles) {
          alert("Añade alguna experiencia laboral para que pueda sugerirte habilidades.");
          return;
      }
      setIsGenerating(true);
      const prompt = `Basado en los siguientes puestos de trabajo: "${jobTitles}", sugiere una lista de 10 habilidades técnicas y blandas relevantes para un currículum. Devuelve solo una lista separada por comas, sin ningún texto adicional.`;
      try {
          const result = await generateWithAI(prompt);
          result.split(',').forEach(skill => addSkill(skill.trim()));
      } catch (error) {
          console.error(error);
          alert("No se pudieron generar sugerencias.");
      } finally {
          setIsGenerating(false);
      }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-text-primary">Habilidades</h2>
        <AIButton onClick={handleAISuggestions}>Sugerir Habilidades</AIButton>
      </div>
      <div>
        <label htmlFor="skill-input" className="form-label">Añadir Habilidad</label>
        <div className="flex gap-2">
          <input
            id="skill-input"
            type="text"
            value={newSkill}
            onChange={(e) => setNewSkill(e.target.value)}
            onKeyDown={handleKeyDown}
            className="form-input flex-grow"
            placeholder="Ej: React, Liderazgo de equipos"
          />
          <button onClick={handleAddSkill} className="px-4 py-2 bg-kai-primary text-white rounded-lg">Añadir</button>
        </div>
      </div>
      <div className="flex flex-wrap gap-2 pt-4">
        {skills.map(skill => (
          <motion.div
            key={skill.id}
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex items-center bg-kai-surface px-3 py-1.5 rounded-full text-sm font-medium"
          >
            {skill.name}
            <button onClick={() => removeSkill(skill.id)} className="ml-2 text-text-secondary hover:text-white">
              <X size={14} />
            </button>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default SkillsStep;
