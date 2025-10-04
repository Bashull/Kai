import React from 'react';
import { useResumeStore } from '../../store/resumeStore';
import { StepIndicator } from '../StepIndicator';
import PersonalInfoStep from '../steps/PersonalInfoStep';
import ExperienceStep from '../steps/ExperienceStep';
import EducationStep from '../steps/EducationStep';
import SkillsStep from '../steps/SkillsStep';
import SummaryStep from '../steps/SummaryStep';
import { ResumePreview } from '../ResumePreview';

const stepComponents = [
    PersonalInfoStep,
    ExperienceStep,
    EducationStep,
    SkillsStep,
    SummaryStep,
];
const stepNames = ["Personal Info", "Experience", "Education", "Skills", "Summary"];

const ResumeBuilderPanel: React.FC = () => {
    const { currentStep, accentColor } = useResumeStore(state => ({
        currentStep: state.currentStep,
        accentColor: state.accentColor,
    }));
    const CurrentStepComponent = stepComponents[currentStep];

    return (
        <div>
            <h1 className="h1-title">Resume Builder</h1>
            <p className="p-subtitle">Create a professional resume with AI assistance, step by step.</p>
            
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 mt-6">
                {/* Left column: Wizard */}
                <div className="lg:col-span-2 flex flex-col gap-6">
                    <StepIndicator steps={stepNames} currentStep={currentStep} accentColor={accentColor} />
                    <div className="panel-container">
                        {CurrentStepComponent && <CurrentStepComponent />}
                    </div>
                </div>

                {/* Right column: Preview */}
                <div className="lg:col-span-3">
                   <div className="sticky top-8">
                        <ResumePreview />
                   </div>
                </div>
            </div>
        </div>
    );
};
export default ResumeBuilderPanel;