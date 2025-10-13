import React from 'react';
import { useAppStore } from '../../store/useAppStore';
import Button from '../ui/Button';
import { Plus, Trash2 } from 'lucide-react';
import { Education } from '../../types';

const EducationItem: React.FC<{ item: Education; index: number }> = ({ item, index }) => {
  const { updateEducation, removeEducation } = useAppStore();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    updateEducation(index, e.target.name as keyof Education, e.target.value);
  };

  return (
    <div className="space-y-4 p-4 border border-border-color rounded-lg">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <input name="institution" value={item.institution} onChange={handleChange} placeholder="Institución" className="form-input" />
        <input name="degree" value={item.degree} onChange={handleChange} placeholder="Título" className="form-input" />
        <input name="fieldOfStudy" value={item.fieldOfStudy} onChange={handleChange} placeholder="Campo de Estudio" className="form-input" />
        <div className="flex items-center gap-4">
          <input name="startDate" type="month" value={item.startDate} onChange={handleChange} className="form-input" />
          <span>-</span>
          <input name="endDate" type="month" value={item.endDate} onChange={handleChange} className="form-input" />
        </div>
      </div>
      <Button onClick={() => removeEducation(item.id)} variant="ghost" size="sm" icon={Trash2}>Eliminar Educación</Button>
    </div>
  );
};

const EducationStep: React.FC = () => {
  const { education, addEducation } = useAppStore(state => ({
    education: state.resumeData.education,
    addEducation: state.addEducation,
  }));

  return (
    <div className="space-y-6">
       <div className="flex justify-between items-center">
         <h2 className="text-xl font-bold text-text-primary">Educación</h2>
         <Button onClick={addEducation} icon={Plus} variant="secondary">Añadir Educación</Button>
      </div>
      <div className="space-y-4 max-h-[calc(100vh-30rem)] overflow-y-auto pr-2">
        {education.map((item, index) => (
          <EducationItem key={item.id} item={item} index={index} />
        ))}
      </div>
    </div>
  );
};

export default EducationStep;