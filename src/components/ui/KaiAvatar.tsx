import React from 'react';
import { motion } from 'framer-motion';

interface KaiAvatarProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  isBusy?: boolean;
}

const KaiAvatar: React.FC<KaiAvatarProps> = ({ size = 'md', className = '', isBusy = false }) => {
  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-16 h-16',
  };

  const avatarVariants = {
    initial: { scale: 0.8, opacity: 0 },
    animate: { scale: 1, opacity: 1 },
  };

  const borderTransition = {
    duration: 2.5,
    repeat: Infinity,
    // FIX: Corrected typing for framer-motion transition properties
    repeatType: 'reverse' as const,
    ease: 'easeInOut' as const,
  };

  const coreTransition = {
    duration: isBusy ? 0.4 : 1.8,
    repeat: Infinity,
    // FIX: Corrected typing for framer-motion transition properties
    repeatType: 'reverse' as const,
    ease: 'easeInOut' as const,
  };


  return (
    <motion.div
      className={`relative rounded-full flex-shrink-0 ${sizeClasses[size]} ${className}`}
      variants={avatarVariants}
      initial="initial"
      animate="animate"
      transition={{ delay: 0.2, type: 'spring', stiffness: 200, damping: 20 }}
    >
      <motion.div 
        className="absolute inset-0 bg-kai-primary rounded-full"
        animate={{
           boxShadow: [
            "0 0 2px 0px rgba(79, 70, 229, 0.7)",
            "0 0 8px 1px rgba(79, 70, 229, 0.5)",
            "0 0 2px 0px rgba(79, 70, 229, 0.7)",
          ],
        }}
        transition={borderTransition}
      />
      <div className="relative w-full h-full bg-kai-dark rounded-full flex items-center justify-center p-1">
        <div className="w-full h-full bg-gradient-to-br from-kai-surface to-kai-dark rounded-full flex items-center justify-center">
            <motion.div
              className="w-2/3 h-2/3 bg-kai-green rounded-full"
              animate={{
                scale: isBusy ? [1, 1.15, 1] : [1, 1.05, 1],
                boxShadow: isBusy
                  ? [
                      "0 0 8px rgba(57, 255, 20, 0.8)",
                      "0 0 24px rgba(57, 255, 20, 1)",
                      "0 0 8px rgba(57, 255, 20, 0.8)",
                    ]
                  : [
                      "0 0 4px rgba(57, 255, 20, 0.5)",
                      "0 0 12px rgba(57, 255, 20, 0.7)",
                      "0 0 4px rgba(57, 255, 20, 0.5)",
                    ],
              }}
              transition={coreTransition}
            />
        </div>
      </div>
    </motion.div>
  );
};

export default KaiAvatar;