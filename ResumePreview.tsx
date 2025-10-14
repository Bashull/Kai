import React, { useState, useRef } from 'react';
import { useAppStore } from './src/store/useAppStore';
import ClassicTemplate from './src/components/templates/ClassicTemplate';
import ModernTemplate from './src/components/templates/ModernTemplate';
import Button from './src/components/ui/Button';
import { Download } from 'lucide-react';

type Template = 'classic' | 'modern';

const templates: { [key in Template]: React.FC } = {
  classic: ClassicTemplate,
  modern: ModernTemplate,
};

const ResumePreview: React.FC = () => {
  const [activeTemplate, setActiveTemplate] = useState<Template>('classic');
  const resumeRef = useRef<HTMLDivElement>(null);

  const handlePrint = () => {
    const printContent = resumeRef.current;
    if (printContent) {
        const title = document.title;
        const resumeData = useAppStore.getState().resumeData;
        const filename = `${resumeData.personalInfo.fullName.replace(' ', '_')}_Resume.pdf`
        document.title = filename;
        window.print();
        document.title = title;
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div className="flex gap-2">
            <h2 className="text-xl font-bold text-text-primary">Vista Previa del CV</h2>
        </div>
        <div className="flex items-center gap-4">
          <div>
            <span className="text-sm font-medium text-text-secondary mr-2">Plantilla:</span>
            <Button onClick={() => setActiveTemplate('classic')} variant={activeTemplate === 'classic' ? 'primary' : 'secondary'} size="sm">Clásica</Button>
            <Button onClick={() => setActiveTemplate('modern')} variant={activeTemplate === 'modern' ? 'primary' : 'secondary'} size="sm" className="ml-2">Moderna</Button>
          </div>
          <Button onClick={handlePrint} icon={Download}>Descargar como PDF</Button>
        </div>
      </div>
      
      <div id="resume-preview" ref={resumeRef} className="bg-white text-gray-800 p-2 rounded-lg shadow-lg max-h-[calc(100vh-32rem)] overflow-y-auto">
        {React.createElement(templates[activeTemplate])}
      </div>
    </div>
  );
};

export default ResumePreview;