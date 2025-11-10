/**
 * Resume Store Service
 * 
 * Provides utility functions for managing resume data,
 * import/export functionality, and validation.
 */

import { ResumeData } from '../types';

/**
 * Validate resume data for completeness
 */
export const validateResumeData = (data: ResumeData): { 
  isValid: boolean; 
  errors: string[] 
} => {
  const errors: string[] = [];

  // Validate personal info
  if (!data.personalInfo.fullName?.trim()) {
    errors.push('Nombre completo es requerido');
  }
  if (!data.personalInfo.email?.trim()) {
    errors.push('Email es requerido');
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.personalInfo.email)) {
    errors.push('Email no es válido');
  }

  // Validate experience
  if (data.experience.length === 0) {
    errors.push('Al menos una experiencia laboral es recomendada');
  }

  // Validate education
  if (data.education.length === 0) {
    errors.push('Al menos una educación es recomendada');
  }

  // Validate skills
  if (data.skills.length === 0) {
    errors.push('Al menos una habilidad es recomendada');
  }

  return {
    isValid: errors.length === 0,
    errors
  };
};

/**
 * Export resume data as JSON
 */
export const exportResumeAsJSON = (data: ResumeData): void => {
  const dataStr = JSON.stringify(data, null, 2);
  const blob = new Blob([dataStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.href = url;
  link.download = `${data.personalInfo.fullName.replace(/\s+/g, '_')}_Resume.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

/**
 * Import resume data from JSON file
 */
export const importResumeFromJSON = (file: File): Promise<ResumeData> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string);
        resolve(data as ResumeData);
      } catch (error) {
        reject(new Error('Archivo JSON inválido'));
      }
    };
    
    reader.onerror = () => reject(new Error('Error al leer el archivo'));
    reader.readAsText(file);
  });
};

/**
 * Generate a resume summary from experience and skills using AI prompt
 */
export const generateResumeSummaryPrompt = (data: ResumeData): string => {
  const { personalInfo, experience, education, skills } = data;
  
  const experienceSummary = experience.map(exp => 
    `${exp.jobTitle} en ${exp.company}`
  ).join(', ');
  
  const educationSummary = education.map(edu => 
    `${edu.degree} en ${edu.fieldOfStudy} de ${edu.institution}`
  ).join(', ');
  
  const skillsList = skills.map(s => s.name).join(', ');
  
  return `Genera un resumen profesional para un CV de una persona llamada ${personalInfo.fullName}. 
Experiencia: ${experienceSummary || 'N/A'}. 
Educación: ${educationSummary || 'N/A'}. 
Habilidades: ${skillsList || 'N/A'}. 
El resumen debe ser conciso, profesional y destacar los logros principales en 2-3 párrafos.`;
};

/**
 * Calculate completeness percentage of resume
 */
export const calculateResumeCompleteness = (data: ResumeData): number => {
  let completed = 0;
  let total = 0;

  // Personal info (5 fields)
  const personalInfoFields = Object.values(data.personalInfo);
  total += personalInfoFields.length;
  completed += personalInfoFields.filter(v => v && v.trim()).length;

  // Experience (at least 1)
  total += 1;
  if (data.experience.length > 0) completed += 1;

  // Education (at least 1)
  total += 1;
  if (data.education.length > 0) completed += 1;

  // Skills (at least 3)
  total += 1;
  if (data.skills.length >= 3) completed += 1;

  // Summary
  total += 1;
  if (data.summary && data.summary.trim()) completed += 1;

  return Math.round((completed / total) * 100);
};

export const ResumeStoreService = {
  validate: validateResumeData,
  exportJSON: exportResumeAsJSON,
  importJSON: importResumeFromJSON,
  generateSummaryPrompt: generateResumeSummaryPrompt,
  calculateCompleteness: calculateResumeCompleteness,
};

export default ResumeStoreService;
