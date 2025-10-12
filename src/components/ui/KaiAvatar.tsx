
import React from 'react';
import { motion } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';

const KaiAvatar: React.FC = () => {
  const isBusy = useAppStore(state =>
    state.isTyping || state.isGeneratingCode || state.isGeneratingImages || state.isChecking || state.isGenerating
  );

  const containerVariants = {
    idle: {
      boxShadow: '0 0 8px rgba(57, 255, 20, 0.4), 0 0 12px rgba(57, 255, 20, 0.3)',
    },
    busy: {
      boxShadow: '0 0 15px var(--kai-green), 0 0 25px var(--kai-green)',
    },
  };

  const smileVariants = {
    idle: { opacity: 1, transition: { delay: 0.2, duration: 0.3 } },
    busy: { opacity: 0, transition: { duration: 0.1 } },
  };
  
  const pupilVariants = {
    idle: { d: "M 20 24 L 28 24" },
    busy: { d: "M 23 24 L 25 24" },
  };

  const circuitTransition = {
    duration: isBusy ? 0.7 : 2,
    repeat: Infinity,
    ease: 'linear'
  }

  return (
    <div className="fixed bottom-6 right-6 z-50" style={{ perspective: '800px' }}>
      <motion.div
        title={isBusy ? "Kai está trabajando..." : "Hola, soy Kai"}
        aria-label="Kai AI Avatar"
        whileHover={{ scale: 1.1, rotateY: 15, rotateX: -10 }}
        transition={{ type: 'spring', stiffness: 200, damping: 20 }}
      >
        <motion.div
          className="w-16 h-16 bg-kai-dark border-2 border-[rgba(57,255,20,0.5)] rounded-full flex items-center justify-center"
          variants={containerVariants}
          animate={isBusy ? "busy" : "idle"}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            ease: "easeInOut",
            repeatType: 'reverse'
          }}
        >
          <motion.svg
            width="52"
            height="52"
            viewBox="0 0 52 52"
            xmlns="http://www.w3.org/2000/svg"
            aria-label="Ilustración del avatar Kai"
          >
            <defs>
              <filter id="kai-glow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="2" result="coloredBlur" />
                <feMerge>
                  <feMergeNode in="coloredBlur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
               <linearGradient id="faceplate-grad" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style={{ stopColor: '#2d3748', stopOpacity: 1 }} />
                <stop offset="100%" style={{ stopColor: '#1a202c', stopOpacity: 1 }} />
              </linearGradient>
            </defs>
            
            {/* Exoskeleton */}
            <path 
              d="M26 4 C14.95 4 6 12.95 6 24 C6 32 10 40 18 44 L22 48 L30 48 L34 44 C42 40 46 32 46 24 C46 12.95 37.05 4 26 4 Z"
              fill="var(--kai-surface)"
              stroke="#374151"
              strokeWidth="1.5"
            />
            
            {/* Faceplate */}
             <path 
              d="M12 16 C12 14, 14 12, 16 12 H36 C38 12, 40 14, 40 16 V34 C40 36, 38 38, 36 38 H16 C14 38, 12 36, 12 34 Z"
              fill="url(#faceplate-grad)"
            />

            {/* Neon Circuits */}
            <g filter="url(#kai-glow)">
                {/* Right Circuit */}
                <motion.path
                  d="M44,28 C40,22 38,18 40,14"
                  stroke="var(--kai-green)" strokeWidth="1" fill="none"
                  strokeDasharray="4 8"
                  animate={{ strokeDashoffset: [0, 12] }}
                  transition={circuitTransition}
                />
                {/* Left Circuit */}
                 <motion.path
                  d="M8,28 C12,22 14,18 12,14"
                  stroke="var(--kai-green)" strokeWidth="1" fill="none"
                  strokeDasharray="4 8"
                  animate={{ strokeDashoffset: [0, -12] }}
                  transition={circuitTransition}
                />
                {/* Top Circuit */}
                 <motion.path
                  d="M20,8 C23,10 29,10 32,8"
                  stroke="var(--kai-green)" strokeWidth="1" fill="none"
                />
            </g>
            
            {/* Visor */}
            <g filter="url(#kai-glow)">
              <path 
                d="M14 20 C14 19.4477 14.4477 19 15 19 H37 C37.5523 19 38 19.4477 38 20 V28 C38 28.5523 37.5523 29 37 29 H15 C14.4477 29 14 28.5523 14 28 V20 Z"
                fill="var(--kai-green)"
              />
              {/* Pupil */}
              <motion.path
                stroke="var(--kai-dark)"
                strokeWidth="2.5"
                strokeLinecap="round"
                variants={pupilVariants}
                animate={isBusy ? "busy" : "idle"}
                transition={{ type: 'spring', stiffness: 400, damping: 20 }}
              />
            </g>

            {/* Holographic Smile */}
            <motion.path
              d="M20 35 Q26 37, 32 35"
              stroke="var(--kai-green)"
              strokeWidth="1.5"
              fill="none"
              strokeLinecap="round"
              filter="url(#kai-glow)"
              variants={smileVariants}
              animate={isBusy ? "busy" : "idle"}
            />
          </motion.svg>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default KaiAvatar;
