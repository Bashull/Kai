import React from 'react';
import Button from './ui/Button';
import { Sparkles } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';

interface AIButtonProps {
    onClick: () => void;
    promptText?: string;
    className?: string;
    children: React.ReactNode;
}

export const AIButton: React.FC<AIButtonProps> = ({ onClick, promptText, className, children }) => {
    const { isGenerating } = useAppStore();

    return (
        <Button
            onClick={onClick}
            loading={isGenerating}
            disabled={isGenerating}
            icon={Sparkles}
            variant="ghost"
            size="sm"
            className={`text-kai-primary ${className}`}
            title={promptText || "Asistencia de IA"}
        >
            {children}
        </Button>
    );
};
