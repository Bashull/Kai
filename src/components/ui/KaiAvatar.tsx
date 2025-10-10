
import React from 'react';
import { motion } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';

const KaiAvatar: React.FC = () => {
  const isBusy = useAppStore(state =>
    state.isTyping || state.isGeneratingCode || state.isGeneratingImages || state.isChecking || state.isGenerating
  );

  const eyeVariants = {
    idle: {
      filter: 'drop-shadow(0 0 2px #39ff14)',
      transition: {
        duration: 2.5,
        repeat: Infinity,
        repeatType: 'reverse',
        ease: 'easeInOut'
      }
    },
    busy: {
      filter: 'drop-shadow(0 0 5px #39ff14) drop-shadow(0 0 10px #39ff14)',
      transition: {
        duration: 0.5,
        repeat: Infinity,
        repeatType: 'reverse',
        ease: 'easeInOut'
      }
    }
  };


  return (
    <div className="fixed bottom-6 right-6 z-50" style={{ perspective: '800px' }}>
      <motion.div
        title={isBusy ? "Kai está trabajando..." : "Hola, soy Kai"}
        aria-label="Kai AI Avatar"
        whileHover={{ scale: 1.1, rotateY: 15, rotateX: -10 }}
        transition={{ type: 'spring', stiffness: 200, damping: 20 }}
      >
        <motion.div
          className="w-16 h-16 bg-kai-surface border-2 border-kai-green rounded-full flex items-center justify-center shadow-lg"
          animate={{
            boxShadow: isBusy
              ? '0 0 20px var(--kai-green), 0 0 30px var(--kai-green)'
              : '0 0 10px rgba(57, 255, 20, 0.5)',
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut",
            repeatType: 'reverse'
          }}
        >
          <motion.svg
            width="48"
            height="48"
            viewBox="0 0 48 48"
            xmlns="http://www.w3.org/2000/svg"
            animate={isBusy ? "busy" : "idle"}
            aria-label="Ilustración del avatar Kai"
          >
            {/* Head Outline */}
            <motion.path
              d="M24,4 C12.954,4 4,12.954 4,24 C4,35.046 12.954,44 24,44 C35.046,44 44,35.046 44,24 C44,12.954 35.046,4 24,4 Z"
              stroke="var(--text-secondary)"
              strokeWidth="1.5"
              fill="var(--kai-dark)"
            />
            {/* Visor/Eye */}
            <motion.path
              d="M12 20 C12 19.4477 12.4477 19 13 19 H35 C35.5523 19 36 19.4477 36 20 V28 C36 28.5523 35.5523 29 35 29 H13 C12.4477 29 12 28.5523 12 28 V20 Z"
              fill="var(--kai-green)"
              variants={eyeVariants}
            />
            {/* Pupil Slit */}
             <motion.line
              x1="22" y1="24" x2="26" y2="24"
              stroke="var(--kai-dark)"
              strokeWidth="3"
              strokeLinecap="round"
            />
            {/* Mouth line */}
             <motion.path
                d="M16 34 C20 32, 28 32, 32 34"
                stroke="var(--text-secondary)"
                strokeWidth="1.5"
                fill="none"
                strokeLinecap="round"
             />
          </motion.svg>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default KaiAvatar;
