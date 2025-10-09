import React from 'react';
import { Mail, Phone, MapPin } from 'lucide-react';
import { ResumeData } from '../../types';
import { Section, IconText } from '../common';

export const ClassicTemplate: React.FC<{ data: ResumeData }> = ({ data }) => {
    const { personalInfo, summary, experience, education, skills, accentColor } = data;
    return (
        <div className="font-serif">
            {/* Header */}
            <div className="text-center border-b-2 pb-4" style={{ borderColor: accentColor }}>
                <h1 className="text-4xl font-bold text-gray-900">{personalInfo.fullName || 'Your Name'}</h1>
                <div className="flex justify-center items-center flex-wrap gap-x-4 gap-y-1 mt-2 text-gray-600 text-sm">
                    <IconText icon={Mail} text={personalInfo.email} />
                    <IconText icon={Phone} text={personalInfo.phoneNumber} />
                    <IconText icon={MapPin} text={personalInfo.address} />
                </div>
            </div>

            {/* Summary */}
            {/* FIX: Removed parentheses to fix children property missing error */}
            {summary &&
                <Section title="Summary">
                    <p className="text-sm text-gray-700 leading-relaxed">{summary}</p>
                </Section>
            }
            
            {/* Experience */}
            {/* FIX: Removed parentheses to fix children property missing error */}
            {experience.length > 0 &&
                 <Section title="Experience">
                    {experience.map((exp) => (
                        <div key={exp.id} className="mb-4">
                            <h3 className="font-bold text-md">{exp.role || "Role"}</h3>
                            <div className="flex justify-between text-sm text-gray-600">
                                <span>{exp.company || "Company"}</span>
                                <span className="font-medium">{exp.startDate} - {exp.endDate || 'Present'}</span>
                            </div>
                            <ul className="list-disc list-inside mt-1">
                                {exp.description.split('\n').map((line, i) => line.trim() && <li key={i} className="text-sm text-gray-700 whitespace-pre-wrap">{line.replace(/•\s*/,'')}</li>)}
                            </ul>
                        </div>
                    ))}
                </Section>
            }
            {/* Education */}
            {/* FIX: Removed parentheses to fix children property missing error */}
            {education.length > 0 &&
                 <Section title="Education">
                    {education.map((edu) => (
                        <div key={edu.id} className="mb-3">
                            <h3 className="font-bold text-md">{edu.degree || "Degree"}</h3>
                            <div className="flex justify-between text-sm text-gray-600">
                                <span>{edu.institution || "Institution"}</span>
                                <span className="font-medium">{edu.startDate} - {edu.endDate}</span>
                            </div>
                        </div>
                    ))}
                </Section>
            }
            {/* Skills */}
            {/* FIX: Removed parentheses to fix children property missing error */}
            {skills.length > 0 &&
                <Section title="Skills">
                    <p className="text-sm text-gray-700">
                        {skills.join(' · ')}
                    </p>
                </Section>
            }
        </div>
    );
};