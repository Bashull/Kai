import { ResumeSlice, AppSlice, ResumeData } from '../../types';
import { generateId } from '../../utils/helpers';

const initialResumeData: ResumeData = {
  personalInfo: {
    fullName: '',
    email: '',
    phoneNumber: '',
    address: '',
    website: '',
  },
  experience: [],
  education: [],
  skills: [],
  summary: '',
};

export const createResumeSlice: AppSlice<ResumeSlice> = (set, get) => ({
  currentStep: 0,
  resumeData: initialResumeData,
  isGenerating: false,
  setCurrentStep: (step: number) => set({ currentStep: step }),
  setResumeData: (data: Partial<ResumeData>) => set(state => ({
    resumeData: { ...state.resumeData, ...data }
  })),
  updatePersonalInfo: (field, value) => set(state => ({
    resumeData: {
      ...state.resumeData,
      personalInfo: { ...state.resumeData.personalInfo, [field]: value }
    }
  })),
  addExperience: () => set(state => ({
    resumeData: {
      ...state.resumeData,
      experience: [...state.resumeData.experience, {
        id: generateId(), jobTitle: '', company: '', location: '',
        startDate: '', endDate: '', isCurrent: false, description: ''
      }]
    }
  })),
  updateExperience: (index, field, value) => set(state => {
    const newExperience = [...state.resumeData.experience];
    (newExperience[index] as any)[field] = value;
    return { resumeData: { ...state.resumeData, experience: newExperience } };
  }),
  removeExperience: (id: string) => set(state => ({
    resumeData: {
      ...state.resumeData,
      experience: state.resumeData.experience.filter(exp => exp.id !== id)
    }
  })),
  addEducation: () => set(state => ({
    resumeData: {
      ...state.resumeData,
      education: [...state.resumeData.education, {
        id: generateId(), institution: '', degree: '', fieldOfStudy: '',
        startDate: '', endDate: ''
      }]
    }
  })),
  updateEducation: (index, field, value) => set(state => {
    const newEducation = [...state.resumeData.education];
    (newEducation[index] as any)[field] = value;
    return { resumeData: { ...state.resumeData, education: newEducation } };
  }),
  removeEducation: (id: string) => set(state => ({
    resumeData: {
      ...state.resumeData,
      education: state.resumeData.education.filter(edu => edu.id !== id)
    }
  })),
  addSkill: (name: string) => {
    if (!name.trim() || get().resumeData.skills.some(s => s.name.toLowerCase() === name.toLowerCase())) return;
    set(state => ({
      resumeData: {
        ...state.resumeData,
        skills: [...state.resumeData.skills, { id: generateId(), name: name.trim() }]
      }
    }));
  },
  removeSkill: (id: string) => set(state => ({
    resumeData: {
      ...state.resumeData,
      skills: state.resumeData.skills.filter(skill => skill.id !== id)
    }
  })),
  setSummary: (summary: string) => set(state => ({
    resumeData: { ...state.resumeData, summary }
  })),
  setIsGenerating: (isGenerating: boolean) => set({ isGenerating }),
});
