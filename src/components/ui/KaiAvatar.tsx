import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';

const KaiAvatar: React.FC = () => {
  const { isTyping } = useAppStore();

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-center">
      <motion.div
        animate={{
          scale: isTyping ? [1, 1.1, 1] : 1,
          boxShadow: isTyping
            ? '0 0 0 8px rgba(79, 70, 229, 0.5)'
            : '0 4px 12px rgba(0,0,0,0.2)',
        }}
        transition={{ duration: 0.8, repeat: isTyping ? Infinity : 0 }}
        className="w-16 h-16 flex items-center justify-center text-3xl font-bold rounded-full bg-kai-primary shadow-xl border-4 border-gray-900 select-none"
        aria-label="Avatar de Kai"
      >
        🤖
      </motion.div>
      <AnimatePresence>
        {isTyping && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            className="text-xs text-kai-primary font-semibold mt-2 px-2 py-0.5 bg-gray-950/50 rounded"
          >
            Kai está pensando...
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default KaiAvatar;
