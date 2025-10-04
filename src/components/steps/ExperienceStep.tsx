import React, { useState } from 'react';
import { useResumeStore } from '../../store/resumeStore';
import { generateWithAI } from '../../services/geminiService';
import { Sparkles, Trash2, Loader } from 'lucide-react';

const ExperienceStep: React.FC = () => {
  const { experience, addExperience, updateExperience, removeExperience, nextStep, prevStep } = useResumeStore();
  const [loadingStates, setLoadingStates] = useState<Record<string, boolean>>({});

  const handleGenerateDescription = async (index: number) => {
    const currentExperience = experience[index];
    if (!currentExperience.role || !currentExperience.company) {
      alert("Please fill in the Role and Company name first.");
      return;
    }
    setLoadingStates(prev => ({ ...prev, [currentExperience.id]: true }));
    const prompt = `Write 3-4 professional, action-oriented bullet points for a resume. The role is "${currentExperience.role}" at "${currentExperience.company}". Focus on achievements and responsibilities.`;
    const generatedDesc = await generateWithAI(prompt);
    updateExperience(index, 'description', generatedDesc);
    setLoadingStates(prev => ({ ...prev, [currentExperience.id]: false }));
  };

  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-2xl font-bold text-green-400">Work Experience</h2>
      {experience.map((exp, index) => (
        <div key={exp.id} className="bg-gray-800 p-4 rounded-lg border border-gray-700 flex flex-col gap-4">
          <div className="flex justify-between items-center">
             <h3 className="font-semibold">Experience #{index + 1}</h3>
             <button onClick={() => removeExperience(exp.id)} className="btn-danger"><Trash2 size={14}/></button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="form-label">Role / Position</label>
              <input type="text" value={exp.role} onChange={e => updateExperience(index, 'role', e.target.value)} className="form-input" />
            </div>
            <div>
              <label className="form-label">Company</label>
              <input type="text" value={exp.company} onChange={e => updateExperience(index, 'company', e.target.value)} className="form-input" />
            </div>
            <div>
              <label className="form-label">Start Date</label>
              <input type="text" placeholder="e.g., Jan 2020" value={exp.startDate} onChange={e => updateExperience(index, 'startDate', e.target.value)} className="form-input" />
            </div>
            <div>
              <label className="form-label">End Date</label>
              <input type="text" placeholder="e.g., Present" value={exp.endDate} onChange={e => updateExperience(index, 'endDate', e.target.value)} className="form-input" />
            </div>
          </div>
          <div>
            <label className="form-label">Description / Achievements</label>
            <textarea value={exp.description} onChange={e => updateExperience(index, 'description', e.target.value)} className="form-textarea" />
            <button onClick={() => handleGenerateDescription(index)} disabled={loadingStates[exp.id]} className="btn-secondary mt-2 text-sm py-1 px-3 w-full md:w-auto">
              {loadingStates[exp.id] ? <Loader size={16} className="animate-spin" /> : <Sparkles size={16} />}
              Ask Kai to Write This
            </button>
          </div>
        </div>
      ))}
      <button onClick={addExperience} className="btn-secondary">+ Add Another Experience</button>
      <div className="flex justify-between mt-4">
        <button onClick={prevStep} className="btn-secondary">Back</button>
        <button onClick={nextStep} className="btn-primary">Next: Education</button>
      </div>
    </div>
  );
};

export default ExperienceStep;
