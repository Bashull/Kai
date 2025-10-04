import React, { useState } from 'react';
import { useResumeStore } from '../../store/resumeStore';
import { generateWithAI } from '../../services/geminiService';
import { Sparkles, Loader } from 'lucide-react';

const SummaryStep: React.FC = () => {
  const { summary, setSummary, prevStep, personalInfo, experience, skills } = useResumeStore();
  const [isLoading, setIsLoading] = useState(false);

  const handleGenerateSummary = async () => {
      setIsLoading(true);
      const expStr = experience.map(e => `${e.role} at ${e.company}`).join(', ');
      const skillsStr = skills.join(', ');
      
      const prompt = `Write a compelling and professional resume summary for ${personalInfo.fullName || 'a professional'}.
      Key experiences include: ${expStr}.
      Key skills include: ${skillsStr}.
      The summary should be 2-4 sentences long, highlighting their main strengths and career goals.`;
      
      const generatedSummary = await generateWithAI(prompt);
      setSummary(generatedSummary);
      setIsLoading(false);
  };

  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-2xl font-bold text-green-400">Professional Summary</h2>
      <p className="text-gray-400">Write a brief summary of your career, or let Kai write one for you based on the info you've provided.</p>
      <div>
        <textarea
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          className="form-textarea min-h-[150px]"
          placeholder="e.g., A highly motivated Software Engineer with 5+ years of experience..."
        />
        <button onClick={handleGenerateSummary} disabled={isLoading} className="btn-secondary mt-2 text-sm py-1 px-3 w-full md:w-auto">
            {isLoading ? <Loader size={16} className="animate-spin" /> : <Sparkles size={16} />}
            Ask Kai to Write Summary
        </button>
      </div>
      <div className="flex justify-between mt-4">
        <button onClick={prevStep} className="btn-secondary">Back</button>
        <button className="btn-primary" onClick={() => alert('Resume Finished!')}>Finish</button>
      </div>
    </div>
  );
};

export default SummaryStep;
