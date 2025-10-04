import React from 'react';
import { useResumeStore } from '../../store/resumeStore';
import { Trash2 } from 'lucide-react';

const EducationStep: React.FC = () => {
  const { education, addEducation, updateEducation, removeEducation, nextStep, prevStep } = useResumeStore();

  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-2xl font-bold text-green-400">Education</h2>
      {education.map((edu, index) => (
        <div key={edu.id} className="bg-gray-800 p-4 rounded-lg border border-gray-700 flex flex-col gap-4">
            <div className="flex justify-between items-center">
                <h3 className="font-semibold">Education #{index + 1}</h3>
                <button onClick={() => removeEducation(edu.id)} className="btn-danger"><Trash2 size={14}/></button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label className="form-label">Institution / University</label>
                    <input type="text" value={edu.institution} onChange={e => updateEducation(index, 'institution', e.target.value)} className="form-input" />
                </div>
                <div>
                    <label className="form-label">Degree / Certificate</label>
                    <input type="text" value={edu.degree} onChange={e => updateEducation(index, 'degree', e.target.value)} className="form-input" />
                </div>
                <div>
                    <label className="form-label">Start Date</label>
                    <input type="text" placeholder="e.g., Sep 2016" value={edu.startDate} onChange={e => updateEducation(index, 'startDate', e.target.value)} className="form-input" />
                </div>
                <div>
                    <label className="form-label">End Date</label>
                    <input type="text" placeholder="e.g., Jun 2020" value={edu.endDate} onChange={e => updateEducation(index, 'endDate', e.target.value)} className="form-input" />
                </div>
            </div>
        </div>
      ))}
      <button onClick={addEducation} className="btn-secondary">+ Add Another Education</button>
      <div className="flex justify-between mt-4">
        <button onClick={prevStep} className="btn-secondary">Back</button>
        <button onClick={nextStep} className="btn-primary">Next: Skills</button>
      </div>
    </div>
  );
};

export default EducationStep;
