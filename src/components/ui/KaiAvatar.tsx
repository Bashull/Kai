import React from 'react';
import { motion } from 'framer-motion';

interface KaiAvatarProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const KaiAvatar: React.FC<KaiAvatarProps> = ({ size = 'md', className = '' }) => {
  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-16 h-16',
  };

  const avatarVariants = {
    initial: { scale: 0.8, opacity: 0 },
    animate: { scale: 1, opacity: 1 },
  };

  return (
    <motion.div
      className={`relative rounded-full flex-shrink-0 ${sizeClasses[size]} ${className}`}
      variants={avatarVariants}
      initial="initial"
      animate="animate"
      transition={{ delay: 0.2, type: 'spring', stiffness: 200, damping: 20 }}
    >
      <div className="absolute inset-0 bg-kai-primary rounded-full animate-border-glow" />
      <div className="relative w-full h-full bg-kai-dark rounded-full flex items-center justify-center p-1">
        <div className="w-full h-full bg-gradient-to-br from-kai-surface to-kai-dark rounded-full flex items-center justify-center">
            <div className="w-2/3 h-2/3 bg-kai-green rounded-full animate-glow" />
        </div>
      </div>
    </motion.div>
  );
};

export default KaiAvatar;
