import React from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';
import StepIndicator from '../steps/StepIndicator';
import PersonalInfoStep from '../steps/PersonalInfoStep';
import ExperienceStep from '../steps/ExperienceStep';
import EducationStep from '../steps/EducationStep';
import SkillsStep from '../steps/SkillsStep';
import SummaryStep from '../steps/SummaryStep';
import ResumePreview from '../ResumePreview';
import Button from '../ui/Button';
import { RESUME_STEPS } from '../../constants';

const stepComponents = [
  PersonalInfoStep,
  ExperienceStep,
  EducationStep,
  SkillsStep,
  SummaryStep,
  ResumePreview,
];

const ResumeBuilderPanel: React.FC = () => {
  const { currentStep, setCurrentStep } = useAppStore();
  const ActiveStepComponent = stepComponents[currentStep];

  const handleNext = () => {
    if (currentStep < RESUME_STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  return (
    <div>
      <h1 className="h1-title">Constructor de CV Asistido por IA</h1>
      <p className="p-subtitle">Creemos un currículum profesional juntos. Te ayudaré en cada paso.</p>
      
      <div className="mt-8">
        <StepIndicator steps={RESUME_STEPS} currentStep={currentStep} />
        
        <div className="mt-8 panel-container min-h-[calc(100vh-22rem)]">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentStep}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
            >
              <ActiveStepComponent />
            </motion.div>
          </AnimatePresence>
        </div>
        
        <div className="mt-6 flex justify-between">
          <Button onClick={handleBack} disabled={currentStep === 0} variant="secondary">
            Atrás
          </Button>
          <Button onClick={handleNext} disabled={currentStep === RESUME_STEPS.length - 1}>
            Siguiente
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ResumeBuilderPanel;
