import React, { useState } from 'react';
import { useResumeStore } from '../../store/resumeStore';
import { X } from 'lucide-react';

const SkillsStep: React.FC = () => {
  const { skills, addSkill, removeSkill, nextStep, prevStep } = useResumeStore();
  const [currentSkill, setCurrentSkill] = useState('');

  const handleAddSkill = () => {
    if (currentSkill.trim()) {
      addSkill(currentSkill.trim());
      setCurrentSkill('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddSkill();
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-2xl font-bold text-green-400">Skills</h2>
      <p className="text-gray-400">Add your key skills. Press Enter or click "Add" to add a skill.</p>
      <div className="flex gap-2">
        <input
          type="text"
          value={currentSkill}
          onChange={(e) => setCurrentSkill(e.target.value)}
          onKeyDown={handleKeyDown}
          className="form-input flex-grow"
          placeholder="e.g., React, Project Management"
        />
        <button onClick={handleAddSkill} className="btn-secondary">Add</button>
      </div>
      <div className="flex flex-wrap gap-2 mt-2">
        {skills.map((skill, index) => (
          <span key={index} className="flex items-center gap-2 bg-green-800/50 text-green-300 text-sm font-medium px-3 py-1 rounded-full">
            {skill}
            <button onClick={() => removeSkill(index)} className="hover:text-white">
              <X size={14} />
            </button>
          </span>
        ))}
      </div>
      <div className="flex justify-between mt-4">
        <button onClick={prevStep} className="btn-secondary">Back</button>
        <button onClick={nextStep} className="btn-primary">Next: Summary</button>
      </div>
    </div>
  );
};

export default SkillsStep;
