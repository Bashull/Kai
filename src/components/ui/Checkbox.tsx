import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface CheckboxProps {
  id: string;
  checked: boolean;
  onChange: () => void;
  className?: string;
}

const Checkbox: React.FC<CheckboxProps> = ({ id, checked, onChange, className = '' }) => {
  const boxVariants = {
    checked: {
      background: 'var(--kai-primary)',
      borderColor: 'var(--kai-primary)',
    },
    unchecked: {
      background: 'transparent',
      borderColor: 'var(--border-color)',
    },
  };

  const checkVariants = {
    checked: { pathLength: 1, opacity: 1 },
    unchecked: { pathLength: 0, opacity: 0 },
  };

  return (
    <div className={`relative flex items-center ${className}`}>
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="absolute w-6 h-6 opacity-0 cursor-pointer"
        aria-checked={checked}
      />
      <motion.div
        className="w-6 h-6 border-2 rounded-md flex items-center justify-center cursor-pointer"
        variants={boxVariants}
        animate={checked ? 'checked' : 'unchecked'}
        transition={{ duration: 0.2 }}
        aria-hidden="true"
      >
        <AnimatePresence>
          {checked && (
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <motion.path
                d="M5 13l4 4L19 7"
                stroke="white"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
                variants={checkVariants}
                initial="unchecked"
                animate="checked"
                exit="unchecked"
                transition={{ duration: 0.3, ease: 'circOut' }}
              />
            </svg>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
};

export default Checkbox;