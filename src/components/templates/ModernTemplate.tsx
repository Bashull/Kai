import React from 'react';
import { Mail, Phone, MapPin } from 'lucide-react';
import { ResumeData } from '../../types';
import { IconText } from '../common';

const Section: React.FC<{ title: string; children: React.ReactNode, className?: string, accentColor: string}> = ({ title, children, className, accentColor }) => (
    <div className={className}>
        <h2 className="text-sm font-bold uppercase tracking-widest mb-3" style={{ color: accentColor }}>{title}</h2>
        {children}
    </div>
);


export const ModernTemplate: React.FC<{ data: ResumeData }> = ({ data }) => {
    const { personalInfo, summary, experience, education, skills, accentColor } = data;
    return (
        <div className="font-sans flex flex-col md:flex-row gap-8">
            {/* Left Column */}
            <div className="md:w-1/3 text-sm">
                 <h1 className="text-3xl font-bold text-gray-900 mb-2">{personalInfo.fullName || 'Your Name'}</h1>
                 <div className="flex flex-col gap-2 text-gray-600 mb-8">
                    <IconText icon={Mail} text={personalInfo.email} />
                    <IconText icon={Phone} text={personalInfo.phoneNumber} />
                    <IconText icon={MapPin} text={personalInfo.address} />
                 </div>
                 
                 {education.length > 0 && (
                    <Section title="Education" className="mb-6" accentColor={accentColor}>
                        {education.map(edu => (
                            <div key={edu.id} className="mb-3">
                                <h3 className="font-bold text-sm text-gray-800">{edu.degree}</h3>
                                <p className="text-xs text-gray-600">{edu.institution}</p>
                                <p className="text-xs text-gray-500">{edu.startDate} - {edu.endDate}</p>
                            </div>
                        ))}
                    </Section>
                 )}

                 {skills.length > 0 && (
                    <Section title="Skills" accentColor={accentColor}>
                        <div className="flex flex-wrap gap-1.5">
                            {skills.map((skill, i) => (
                                <span key={i} className="bg-gray-200 text-gray-800 text-xs font-medium px-2 py-1 rounded">{skill}</span>
                            ))}
                        </div>
                    </Section>
                 )}
            </div>

            {/* Right Column */}
            <div className="md:w-2/3">
                {summary && (
                    <Section title="Summary" className="mb-6" accentColor={accentColor}>
                        <p className="text-sm text-gray-700 leading-relaxed">{summary}</p>
                    </Section>
                )}
                
                {experience.length > 0 && (
                    <Section title="Experience" accentColor={accentColor}>
                        {experience.map(exp => (
                            <div key={exp.id} className="mb-5">
                                <h3 className="font-bold text-md text-gray-800">{exp.role}</h3>
                                <div className="flex justify-between items-baseline text-sm text-gray-600 mb-1">
                                    <span className="font-semibold">{exp.company}</span>
                                    <span className="text-xs font-medium">{exp.startDate} - {exp.endDate || 'Present'}</span>
                                </div>
                                <ul className="list-disc list-inside">
                                    {exp.description.split('\n').map((line, i) => line.trim() && <li key={i} className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{line.replace(/•\s*/,'')}</li>)}
                                </ul>
                            </div>
                        ))}
                    </Section>
                )}
            </div>
        </div>
    );
};