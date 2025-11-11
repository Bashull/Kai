import React from 'react';
import Button from './Button';
import { Sparkles } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';

interface AIButtonProps extends React.ComponentProps<typeof Button> {
    onClick: () => void;
    promptText?: string;
}

export const AIButton: React.FC<AIButtonProps> = ({ onClick, promptText, className, children, ...props }) => {
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
            {...props}
        >
            {children}
        </Button>
    );
};
