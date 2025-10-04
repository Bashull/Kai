import React from 'react';
import { useResumeStore } from '../../store/resumeStore';

const PersonalInfoStep: React.FC = () => {
  const { personalInfo, setPersonalInfo, nextStep } = useResumeStore();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPersonalInfo({ ...personalInfo, [e.target.name]: e.target.value });
  };

  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-2xl font-bold text-green-400">Personal Information</h2>
      <div>
        <label htmlFor="fullName" className="form-label">Full Name</label>
        <input type="text" name="fullName" id="fullName" value={personalInfo.fullName} onChange={handleChange} className="form-input" />
      </div>
      <div>
        <label htmlFor="email" className="form-label">Email Address</label>
        <input type="email" name="email" id="email" value={personalInfo.email} onChange={handleChange} className="form-input" />
      </div>
      <div>
        <label htmlFor="phoneNumber" className="form-label">Phone Number</label>
        <input type="tel" name="phoneNumber" id="phoneNumber" value={personalInfo.phoneNumber} onChange={handleChange} className="form-input" />
      </div>
      <div>
        <label htmlFor="address" className="form-label">Address (City, Country)</label>
        <input type="text" name="address" id="address" value={personalInfo.address} onChange={handleChange} className="form-input" />
      </div>
      <div className="flex justify-end mt-4">
        <button onClick={nextStep} className="btn-primary">Next: Experience</button>
      </div>
    </div>
  );
};

export default PersonalInfoStep;
