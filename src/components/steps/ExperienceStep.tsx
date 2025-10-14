import React from 'react';
// FIX: Replaced aliased import path with a relative path.
import { useAppStore } from '../../store/useAppStore';
// FIX: Replaced aliased import path with a relative path.
import { generateWithAI } from '../../services/geminiService';
// FIX: Replaced aliased import path with a relative path.
import { AIButton } from '../ui/AIButton';
// FIX: Replaced aliased import path with a relative path.
import Button from '../ui/Button';
import { Plus, Trash2 } from 'lucide-react';
// FIX: Replaced aliased import path with a relative path.
import { Experience } from '../../types';

const ExperienceItem: React.FC<{ item: Experience; index: number }> = ({ item, index }) => {
  const { updateExperience, removeExperience, setIsGenerating, addNotification } = useAppStore();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    updateExperience(index, e.target.name as keyof Experience, e.target.value);
  };
  
  const handleCheckboxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    updateExperience(index, e.target.name as keyof Experience, e.target.checked);
  }

  const handleAIDescription = async () => {
    if (!item.jobTitle || !item.company) {
      addNotification({ type: 'error', message: "Por favor, introduce un Puesto y una Empresa para la asistencia de IA." });
      return;
    }
    setIsGenerating(true);
    const prompt = `Escribe una descripción de trabajo concisa y profesional para un currículum. Puesto: "${item.jobTitle}" en la empresa "${item.company}". Describe 3-4 responsabilidades clave o logros en formato de lista con viñetas.`;
    try {
      const result = await generateWithAI(prompt);
      updateExperience(index, 'description', result);
    } catch (error) {
      console.error(error);
      addNotification({ type: 'error', message: "No se pudo generar la descripción." });
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-4 p-4 border border-border-color rounded-lg">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <input name="jobTitle" value={item.jobTitle} onChange={handleChange} placeholder="Puesto" className="form-input" />
        <input name="company" value={item.company} onChange={handleChange} placeholder="Empresa" className="form-input" />
        <input name="location" value={item.location} onChange={handleChange} placeholder="Ubicación" className="form-input" />
        <div className="flex items-center gap-4">
          <input name="startDate" type="month" value={item.startDate} onChange={handleChange} className="form-input" />
          <span>-</span>
          <input name="endDate" type="month" value={item.endDate} onChange={handleChange} className="form-input" disabled={item.isCurrent}/>
           <div className="flex items-center">
             <input type="checkbox" id={`current-${item.id}`} name="isCurrent" checked={item.isCurrent} onChange={handleCheckboxChange} className="h-4 w-4 rounded border-gray-500 bg-gray-700 text-kai-primary focus:ring-kai-primary" />
             <label htmlFor={`current-${item.id}`} className="ml-2 text-sm text-gray-300">Actual</label>
           </div>
        </div>
      </div>
      <div className="relative">
        <textarea name="description" value={item.description} onChange={handleChange} placeholder="Descripción del puesto y logros..." className="form-textarea" rows={4} />
        <AIButton onClick={handleAIDescription} className="absolute bottom-2 right-2">Mejorar Descripción</AIButton>
      </div>
       <Button onClick={() => removeExperience(item.id)} variant="ghost" size="sm" icon={Trash2}>Eliminar Experiencia</Button>
    </div>
  );
};

const ExperienceStep: React.FC = () => {
  const { experience, addExperience } = useAppStore(state => ({
    experience: state.resumeData.experience,
    addExperience: state.addExperience,
  }));

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
         <h2 className="text-xl font-bold text-text-primary">Experiencia Laboral</h2>
         <Button onClick={addExperience} icon={Plus} variant="secondary">Añadir Experiencia</Button>
      </div>
      <div className="space-y-4 max-h-[calc(100vh-30rem)] overflow-y-auto pr-2">
        {experience.map((item, index) => (
          <ExperienceItem key={item.id} item={item} index={index} />
        ))}
      </div>
    </div>
  );
};

export default ExperienceStep;