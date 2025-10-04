import React from 'react';
import { useResumeStore } from '../store/resumeStore';
import jsPDF from 'jspdf';
import { Download, Palette } from 'lucide-react';
import { ClassicTemplate } from './templates/ClassicTemplate';
import { ModernTemplate } from './templates/ModernTemplate';
import { generateClassicPDF, generateModernPDF } from '../lib/pdf-generators';
import { ACCENT_COLORS } from '../constants';
import { ResumeTemplate } from '../types';

export const ResumePreview: React.FC = () => {
    const resumeData = useResumeStore((state) => state);
    const { template, setTemplate, accentColor, setAccentColor } = resumeData;

    const handleDownload = () => {
        const doc = new jsPDF('p', 'pt', 'a4');
        
        switch(template) {
            case 'modern':
                generateModernPDF(doc, resumeData);
                break;
            case 'classic':
            default:
                generateClassicPDF(doc, resumeData);
                break;
        }
        
        doc.save(`${resumeData.personalInfo.fullName.replace(' ', '_') || 'resume'}.pdf`);
    }
    
    const TemplateButton: React.FC<{name: ResumeTemplate}> = ({ name }) => (
        <button 
            onClick={() => setTemplate(name)}
            className={`capitalize text-xs font-semibold px-3 py-1 rounded-md transition-colors ${template === name ? 'bg-gray-700 text-white' : 'bg-gray-200 hover:bg-gray-300 text-gray-700'}`}>
            {name}
        </button>
    );

    return (
        <div className="bg-white text-gray-800 rounded-lg shadow-2xl overflow-hidden">
            <div className="p-4 bg-gray-100 border-b flex justify-between items-center flex-wrap gap-4">
                <div className='flex items-center gap-4 flex-wrap'>
                    <h3 className="text-lg font-bold text-gray-700">Live Preview</h3>
                    <div className="flex items-center gap-2 bg-white px-2 py-1 rounded-lg border">
                        <TemplateButton name="classic" />
                        <TemplateButton name="modern" />
                    </div>
                     <div className="flex items-center gap-2 bg-white px-2 py-1 rounded-lg border">
                        <Palette size={16} className="text-gray-600"/>
                        {ACCENT_COLORS.map(color => (
                            <button
                                key={color.name}
                                title={color.name}
                                onClick={() => setAccentColor(color.color)}
                                className={`w-5 h-5 rounded-full transition-transform ${accentColor === color.color ? 'ring-2 ring-offset-1 ring-gray-700' : ''}`}
                                style={{ backgroundColor: color.color }}
                            />
                        ))}
                    </div>
                </div>
                <button onClick={handleDownload} className="btn-primary text-sm py-1 px-3">
                    <Download size={16} />
                    Download PDF
                </button>
            </div>
            <div className="p-8" id="resume-content">
               {template === 'classic' && <ClassicTemplate data={resumeData} />}
               {template === 'modern' && <ModernTemplate data={resumeData} />}
            </div>
        </div>
    );
}