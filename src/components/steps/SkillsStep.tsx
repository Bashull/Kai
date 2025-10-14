import React, { useState, useEffect } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { generateWithAI } from '../../services/geminiService';
import { AIButton } from '../ui/AIButton';
import { X } from 'lucide-react';
import { motion } from 'framer-motion';
import { COMMON_SKILLS } from '../../constants';

const SkillsStep: React.FC = () => {
  const { resumeData, addSkill, removeSkill, setIsGenerating, addNotification } = useAppStore();
  const { skills } = resumeData;
  const [newSkill, setNewSkill] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);

  useEffect(() => {
    if (newSkill.trim().length > 1) {
      const lowercasedInput = newSkill.toLowerCase();
      const existingSkillNames = new Set(skills.map(s => s.name.toLowerCase()));
      const filtered = COMMON_SKILLS.filter(s => 
        s.toLowerCase().includes(lowercasedInput) && !existingSkillNames.has(s.toLowerCase())
      ).slice(0, 5);
      setSuggestions(filtered);
    } else {
      setSuggestions([]);
    }
  }, [newSkill, skills]);

  const handleAddSkillFromInput = (skillToAdd: string) => {
    if (skillToAdd.trim()) {
      addSkill(skillToAdd.trim());
      setNewSkill('');
      setSuggestions([]);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      handleAddSkillFromInput(newSkill);
    }
  };

  const handleAISuggestions = async () => {
      const jobTitles = resumeData.experience.map(e => e.jobTitle).join(', ');
      if (!jobTitles) {
          addNotification({ type: 'info', message: "Añade alguna experiencia laboral para que pueda sugerirte habilidades." });
          return;
      }
      setIsGenerating(true);
      const prompt = `Basado en los siguientes puestos de trabajo: "${jobTitles}", sugiere una lista de 10 habilidades técnicas y blandas relevantes para un currículum. Devuelve solo una lista separada por comas, sin ningún texto adicional.`;
      try {
          const result = await generateWithAI(prompt);
          result.split(',').forEach(skill => addSkill(skill.trim()));
      } catch (error) {
          console.error(error);
          addNotification({ type: 'error', message: "No se pudieron generar sugerencias." });
      } finally {
          setIsGenerating(false);
      }
  };

  const suggestionsVariants = {
    initial: { opacity: 0, y: -10 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0 },
  };

  const skillTagVariants = {
    initial: { opacity: 0, scale: 0.5 },
    animate: { opacity: 1, scale: 1 },
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-text-primary">Habilidades</h2>
        <AIButton onClick={handleAISuggestions}>Sugerir Habilidades</AIButton>
      </div>
      <div>
        <label htmlFor="skill-input" className="form-label">Añadir Habilidad</label>
        <div className="relative">
          <div className="flex gap-2">
            <input
              id="skill-input"
              type="text"
              value={newSkill}
              onChange={(e) => setNewSkill(e.target.value)}
              onKeyDown={handleKeyDown}
              className="form-input flex-grow"
              placeholder="Ej: React, Liderazgo de equipos"
              autoComplete="off"
            />
            <button onClick={() => handleAddSkillFromInput(newSkill)} className="px-4 py-2 bg-kai-primary text-white rounded-lg">Añadir</button>
          </div>
          {suggestions.length > 0 && (
            <motion.ul
              variants={suggestionsVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              className="absolute z-10 w-full mt-1 bg-kai-surface border border-border-color rounded-lg shadow-lg max-h-60 overflow-y-auto"
            >
              {suggestions.map(suggestion => (
                <li
                  key={suggestion}
                  onClick={() => handleAddSkillFromInput(suggestion)}
                  onMouseDown={(e) => e.preventDefault()}
                  className="px-4 py-2 text-sm cursor-pointer hover:bg-kai-dark/50"
                >
                  {suggestion}
                </li>
              ))}
            </motion.ul>
          )}
        </div>
      </div>
      <div className="flex flex-wrap gap-2 pt-4">
        {skills.map(skill => (
          <motion.div
            key={skill.id}
            variants={skillTagVariants}
            initial="initial"
            animate="animate"
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