import React from 'react';

export const Section = ({ title, children, className }: { title: string; children: React.ReactNode; className?: string }) => (
    <div className={`mt-6 ${className}`}>
        <h2 className="text-xl font-bold text-gray-800 border-b-2 border-gray-200 pb-1 mb-2">{title}</h2>
        {children}
    </div>
);

export const IconText = ({ icon: Icon, text, className }: { icon: React.ElementType; text: string | undefined; className?: string}) => {
    if (!text) return null;
    return (
        <span className={`flex items-center gap-2 ${className}`}>
            <Icon size={14} className="flex-shrink-0" />
            <span>{text}</span>
        </span>
    );
};
