import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { ResumeStore, ResumeData } from '../types';
import { ACCENT_COLORS } from '../constants';

const initialData: ResumeData = {
  personalInfo: { fullName: '', email: '', phoneNumber: '', address: '' },
  experience: [],
  education: [],
  skills: [],
  summary: '',
  template: 'classic',
  accentColor: ACCENT_COLORS[0].color,
};

export const useResumeStore = create<ResumeStore>()(
  persist(
    (set) => ({
      ...initialData,
      currentStep: 0,
      
      setPersonalInfo: (info) => set({ personalInfo: info }),

      addExperience: () => set((state) => ({
        experience: [...state.experience, { id: Date.now().toString(), company: '', role: '', startDate: '', endDate: '', description: '' }]
      })),
      updateExperience: (index, field, value) => set((state) => {
        const newExperience = [...state.experience];
        newExperience[index] = { ...newExperience[index], [field]: value };
        return { experience: newExperience };
      }),
      removeExperience: (id) => set((state) => ({
        experience: state.experience.filter(exp => exp.id !== id)
      })),

      addEducation: () => set((state) => ({
        education: [...state.education, { id: Date.now().toString(), institution: '', degree: '', startDate: '', endDate: '' }]
      })),
      updateEducation: (index, field, value) => set((state) => {
        const newEducation = [...state.education];
        newEducation[index] = { ...newEducation[index], [field]: value };
        return { education: newEducation };
      }),
      removeEducation: (id) => set((state) => ({
        education: state.education.filter(edu => edu.id !== id)
      })),

      setSkills: (skills) => set({ skills }),
      addSkill: (skill) => set((state) => ({ skills: [...state.skills, skill] })),
      removeSkill: (index) => set((state) => ({
        skills: state.skills.filter((_, i) => i !== index)
      })),
      
      setSummary: (summary) => set({ summary }),

      setTemplate: (template) => set({ template }),
      setAccentColor: (color) => set({ accentColor: color }),

      nextStep: () => set((state) => ({ currentStep: Math.min(state.currentStep + 1, 4) })),
      prevStep: () => set((state) => ({ currentStep: Math.max(state.currentStep - 1, 0) })),
    }),
    {
      name: 'kai-resume-storage', // name of the item in the storage (must be unique)
    }
  )
);
