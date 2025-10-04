import React from 'react';
import { Check } from 'lucide-react';

interface StepIndicatorProps {
  steps: string[];
  currentStep: number;
  accentColor: string;
}

export const StepIndicator: React.FC<StepIndicatorProps> = ({ steps, currentStep, accentColor }) => {
  return (
    <nav aria-label="Progress">
      <ol role="list" className="flex items-center">
        {steps.map((step, stepIdx) => (
          <li key={step} className={`relative ${stepIdx !== steps.length - 1 ? 'pr-8 sm:pr-20' : ''}`}>
            {stepIdx < currentStep ? (
              <>
                <div className="absolute inset-0 flex items-center" aria-hidden="true">
                  <div className="h-0.5 w-full" style={{ backgroundColor: accentColor }} />
                </div>
                <div
                  className="relative flex h-8 w-8 items-center justify-center rounded-full"
                  style={{ backgroundColor: accentColor }}
                >
                  <Check className="h-5 w-5 text-white" aria-hidden="true" />
                </div>
                <span className="absolute top-10 -left-2 w-max text-xs text-gray-300">{step}</span>
              </>
            ) : stepIdx === currentStep ? (
              <>
                <div className="absolute inset-0 flex items-center" aria-hidden="true">
                  <div className="h-0.5 w-full bg-gray-700" />
                </div>
                <div
                  className="relative flex h-8 w-8 items-center justify-center rounded-full border-2 bg-gray-800"
                  style={{ borderColor: accentColor }}
                  aria-current="step"
                >
                  <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: accentColor }} />
                </div>
                <span className="absolute top-10 -left-2 w-max text-xs font-semibold" style={{ color: accentColor }}>{step}</span>
              </>
            ) : (
              <>
                <div className="absolute inset-0 flex items-center" aria-hidden="true">
                  <div className="h-0.5 w-full bg-gray-700" />
                </div>
                <div
                  className="group relative flex h-8 w-8 items-center justify-center rounded-full border-2 border-gray-600 bg-gray-800"
                >
                  <span
                    className="h-2.5 w-2.5 rounded-full bg-transparent"
                    aria-hidden="true"
                  />
                </div>
                <span className="absolute top-10 -left-2 w-max text-xs text-gray-500">{step}</span>
              </>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
};