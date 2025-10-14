import React from 'react';
import { useAppStore } from '../../store/useAppStore';
import { Mail, Phone, MapPin, Globe } from 'lucide-react';

const ModernTemplate: React.FC = () => {
    const { resumeData } = useAppStore();
    const { personalInfo, experience, education, skills, summary } = resumeData;

    return (
        <div className="p-6 font-sans bg-white text-gray-800 text-base flex gap-8">
            <aside className="w-1/3 bg-gray-100 p-4 rounded">
                <h1 className="text-3xl font-bold text-indigo-700">{personalInfo.fullName}</h1>
                <div className="mt-6 space-y-3 text-sm">
                    {personalInfo.email && <p className="flex items-center gap-2"><Mail size={14} className="text-indigo-700"/><span>{personalInfo.email}</span></p>}
                    {personalInfo.phoneNumber && <p className="flex items-center gap-2"><Phone size={14} className="text-indigo-700"/><span>{personalInfo.phoneNumber}</span></p>}
                    {personalInfo.address && <p className="flex items-center gap-2"><MapPin size={14} className="text-indigo-700"/><span>{personalInfo.address}</span></p>}
                    {personalInfo.website && <p className="flex items-center gap-2"><Globe size={14} className="text-indigo-700"/><span>{personalInfo.website}</span></p>}
                </div>

                <div className="mt-8">
                    <h2 className="text-lg font-bold text-indigo-700 border-b-2 border-indigo-200 pb-1 mb-2">Habilidades</h2>
                    <div className="flex flex-wrap gap-2 mt-2">
                        {skills.map(skill => (
                            <span key={skill.id} className="bg-indigo-200 text-indigo-800 text-xs font-semibold px-2.5 py-1 rounded-full">{skill.name}</span>
                        ))}
                    </div>
                </div>
                 <div className="mt-8">
                    <h2 className="text-lg font-bold text-indigo-700 border-b-2 border-indigo-200 pb-1 mb-2">Educación</h2>
                    {education.map(edu => (
                        <div key={edu.id} className="mb-3 text-sm">
                            <h3 className="font-bold">{edu.institution}</h3>
                            <p>{edu.degree}</p>
                            <p className="text-gray-600">{edu.fieldOfStudy}</p>
                            <p className="text-xs text-gray-500">{edu.startDate} - {edu.endDate}</p>
                        </div>
                    ))}
                </div>
            </aside>
            <main className="w-2/3">
                <section>
                    <h2 className="text-2xl font-bold text-indigo-700 border-b-2 border-indigo-200 pb-1 mb-3">Resumen Profesional</h2>
                    <p className="text-sm">{summary}</p>
                </section>
                <section className="mt-6">
                    <h2 className="text-2xl font-bold text-indigo-700 border-b-2 border-indigo-200 pb-1 mb-3">Experiencia Laboral</h2>
                    {experience.map(exp => (
                        <div key={exp.id} className="mb-4">
                            <div className="flex justify-between items-baseline">
                                <h3 className="text-lg font-bold">{exp.jobTitle}</h3>
                                <p className="text-xs text-gray-500">{exp.startDate} - {exp.isCurrent ? 'Actual' : exp.endDate}</p>
                            </div>
                            <p className="font-semibold text-gray-700">{exp.company}, {exp.location}</p>
                             <div className="text-sm mt-1 text-gray-600 whitespace-pre-wrap">{exp.description}</div>
                        </div>
                    ))}
                </section>
            </main>
        </div>
    );
};

export default ModernTemplate;
