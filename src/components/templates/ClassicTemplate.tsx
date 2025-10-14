import React from 'react';
import { useAppStore } from '@/store/useAppStore';
import { Mail, Phone, MapPin, Globe } from 'lucide-react';

const ClassicTemplate: React.FC = () => {
  const { resumeData } = useAppStore();
  const { personalInfo, experience, education, skills, summary } = resumeData;

  return (
    <div className="p-8 font-serif bg-white text-black text-sm">
      <header className="text-center mb-8">
        <h1 className="text-4xl font-bold tracking-wider uppercase">{personalInfo.fullName}</h1>
        <div className="flex justify-center gap-6 mt-2 text-xs">
          {personalInfo.email && <p className="flex items-center gap-1"><Mail size={12}/>{personalInfo.email}</p>}
          {personalInfo.phoneNumber && <p className="flex items-center gap-1"><Phone size={12}/>{personalInfo.phoneNumber}</p>}
          {personalInfo.address && <p className="flex items-center gap-1"><MapPin size={12}/>{personalInfo.address}</p>}
          {personalInfo.website && <p className="flex items-center gap-1"><Globe size={12}/>{personalInfo.website}</p>}
        </div>
      </header>

      <section className="mb-6">
        <h2 className="text-xl font-bold border-b-2 border-black pb-1 mb-2 uppercase tracking-widest">Resumen</h2>
        <p className="text-justify">{summary}</p>
      </section>

      <section className="mb-6">
        <h2 className="text-xl font-bold border-b-2 border-black pb-1 mb-2 uppercase tracking-widest">Experiencia</h2>
        {experience.map(exp => (
          <div key={exp.id} className="mb-4">
            <div className="flex justify-between">
              <h3 className="text-lg font-semibold">{exp.jobTitle}</h3>
              <p className="text-sm font-light">{exp.startDate} - {exp.isCurrent ? 'Actual' : exp.endDate}</p>
            </div>
            <p className="italic">{exp.company}, {exp.location}</p>
            <div className="text-sm mt-1 whitespace-pre-wrap">{exp.description}</div>
          </div>
        ))}
      </section>

      <section className="mb-6">
        <h2 className="text-xl font-bold border-b-2 border-black pb-1 mb-2 uppercase tracking-widest">Educación</h2>
        {education.map(edu => (
          <div key={edu.id} className="mb-2">
             <div className="flex justify-between">
              <h3 className="text-lg font-semibold">{edu.institution}</h3>
              <p className="text-sm font-light">{edu.startDate} - {edu.endDate}</p>
            </div>
            <p className="italic">{edu.degree}, {edu.fieldOfStudy}</p>
          </div>
        ))}
      </section>

      <section>
        <h2 className="text-xl font-bold border-b-2 border-black pb-1 mb-2 uppercase tracking-widest">Habilidades</h2>
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          {skills.map(skill => (
            <span key={skill.id}>{skill.name}</span>
          ))}
        </div>
      </section>
    </div>
  );
};

export default ClassicTemplate;