import React from 'react';

const DynamicBackground: React.FC = () => {
  return (
    <div className="fixed top-0 left-0 w-full h-full -z-10 overflow-hidden">
      <div className="absolute top-0 left-0 w-full h-full bg-kai-dark" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[60rem] h-[60rem] bg-kai-primary/10 rounded-full blur-3xl animate-pulse-slow" />
      <div 
        className="absolute top-1/4 left-1/4 w-[40rem] h-[40rem] bg-kai-green/5 rounded-full blur-3xl animate-pulse-slow" 
        style={{ animationDelay: '2s' }}
      />
    </div>
  );
};

export default DynamicBackground;
