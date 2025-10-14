import React from 'react';
// FIX: Replaced aliased import path with a relative path.
import { useAppStore } from '../../store/useAppStore';
// FIX: Replaced aliased import path with a relative path.
import { PersonalInfo } from '../../types';

const PersonalInfoStep: React.FC = () => {
  const { personalInfo, updatePersonalInfo } = useAppStore(state => ({
    personalInfo: state.resumeData.personalInfo,
    updatePersonalInfo: state.updatePersonalInfo,
  }));

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    updatePersonalInfo(e.target.name as keyof PersonalInfo, e.target.value);
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-text-primary">Información Personal</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label htmlFor="fullName" className="form-label">Nombre Completo</label>
          <input type="text" name="fullName" id="fullName" value={personalInfo.fullName} onChange={handleChange} className="form-input" placeholder="Ej: Jane Doe"/>
        </div>
        <div>
          <label htmlFor="email" className="form-label">Email</label>
          <input type="email" name="email" id="email" value={personalInfo.email} onChange={handleChange} className="form-input" placeholder="Ej: jane.doe@example.com"/>
        </div>
        <div>
          <label htmlFor="phoneNumber" className="form-label">Número de Teléfono</label>
          <input type="tel" name="phoneNumber" id="phoneNumber" value={personalInfo.phoneNumber} onChange={handleChange} className="form-input" placeholder="Ej: (123) 456-7890"/>
        </div>
        <div>
          <label htmlFor="address" className="form-label">Dirección</label>
          <input type="text" name="address" id="address" value={personalInfo.address} onChange={handleChange} className="form-input" placeholder="Ej: Ciudad, País"/>
        </div>
        <div className="md:col-span-2">
          <label htmlFor="website" className="form-label">Sitio Web / LinkedIn / GitHub</label>
          <input type="url" name="website" id="website" value={personalInfo.website} onChange={handleChange} className="form-input" placeholder="Ej: https://linkedin.com/in/janedoe"/>
        </div>
      </div>
    </div>
  );
};

export default PersonalInfoStep;