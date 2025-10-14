import React from 'react';
import { motion } from 'framer-motion';
import { Check } from 'lucide-react';

interface StepIndicatorProps {
  steps: string[];
  currentStep: number;
}

const StepIndicator: React.FC<StepIndicatorProps> = ({ steps, currentStep }) => {
  return (
    <div className="w-full">
      <div className="flex items-center">
        {steps.map((step, index) => (
          <React.Fragment key={step}>
            <div className="flex flex-col items-center">
              {/* FIX: Added @ts-ignore for framer-motion props due to a type definition issue. */}
              {/* @ts-ignore */}
              <motion.div
                animate={currentStep >= index ? "active" : "inactive"}
                variants={{
                  active: { scale: 1.1, backgroundColor: 'var(--kai-primary)', borderColor: 'var(--kai-primary)' },
                  inactive: { scale: 1, backgroundColor: 'var(--kai-surface)', borderColor: 'var(--border-color)' }
                }}
                transition={{ duration: 0.2 }}
                className="w-10 h-10 rounded-full border-2 flex items-center justify-center"
              >
                {currentStep > index ? <Check className="w-6 h-6 text-white" /> : <span className={currentStep === index ? 'text-text-primary' : 'text-text-secondary'}>{index + 1}</span>}
              </motion.div>
              <p className={`mt-2 text-xs text-center ${currentStep >= index ? 'text-text-primary font-semibold' : 'text-text-secondary'}`}>{step}</p>
            </div>
            {index < steps.length - 1 && (
              // FIX: Added @ts-ignore for framer-motion props due to a type definition issue.
              // @ts-ignore
              <motion.div
                className="flex-1 h-1 mx-2 rounded"
                animate={currentStep > index ? "active" : "inactive"}
                variants={{
                  active: { backgroundColor: 'var(--kai-primary)' },
                  inactive: { backgroundColor: 'var(--border-color)' }
                }}
                transition={{ duration: 0.2 }}
              />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};

export default StepIndicator;