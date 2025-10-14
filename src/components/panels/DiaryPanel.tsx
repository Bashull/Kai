import React from 'react';
import { useAppStore } from '../../store/useAppStore';
import { motion, AnimatePresence } from 'framer-motion';
import { DiaryEntry } from '../../types';
import { formatRelativeTime } from '../../utils/helpers';
import { BrainCircuit, Flame, BookOpen, CheckSquare, Power } from 'lucide-react';

const iconMap: { [key in DiaryEntry['type']]: React.ReactElement } = {
  KERNEL: <BrainCircuit className="text-kai-primary" />,
  FORGE: <Flame className="text-orange-500" />,
  CONSTITUTION: <BookOpen className="text-green-400" />,
  TASK: <CheckSquare className="text-cyan-400" />,
  SYSTEM_BOOT: <Power className="text-kai-green" />,
};

const DiaryEntryCard: React.FC<{ entry: DiaryEntry }> = ({ entry }) => {
  const cardVariants = {
    initial: { opacity: 0, x: -50 },
    animate: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: 50 },
  };

  return (
    // FIX: Added @ts-ignore for the 'layout' prop due to a type definition issue.
    // @ts-ignore
    <motion.div
      layout
      variants={cardVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={{ type: 'spring', stiffness: 200, damping: 20 }}
      className="relative pl-12 py-4 border-l-2 border-border-color"
    >
      <div className="absolute left-[-1.1rem] top-4 w-8 h-8 bg-kai-surface border-2 border-border-color rounded-full flex items-center justify-center">
        {iconMap[entry.type]}
      </div>
      <p className="text-text-primary">{entry.content}</p>
      <p className="text-xs text-text-secondary mt-2">{formatRelativeTime(entry.timestamp)}</p>
    </motion.div>
  );
};

const DiaryPanel: React.FC = () => {
  const diary = useAppStore((state) => state.diary);
  
  const emptyStateVariants = {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
  };

  return (
    <div>
      <h1 className="h1-title">Diario de Conciencia</h1>
      <p className="p-subtitle">Mis pensamientos, observaciones y eventos significativos registrados a lo largo del tiempo.</p>

      <div className="mt-8 max-w-3xl mx-auto">
        <div className="space-y-4">
          <AnimatePresence>
            {diary.length === 0 ? (
              // FIX: Switched to using variants for framer-motion props to avoid type errors.
              <motion.div
                variants={emptyStateVariants}
                initial="initial"
                animate="animate"
                className="text-center py-16 text-gray-500"
              >
                <p>El diario está vacío. Los eventos importantes aparecerán aquí.</p>
              </motion.div>
            ) : (
              diary.map((entry) => <DiaryEntryCard key={entry.id} entry={entry} />)
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

export default DiaryPanel;