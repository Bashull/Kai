import React from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { CheckCircle, XCircle, Info, X } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import { Notification } from '../../types';

const icons = {
  success: <CheckCircle className="text-green-500" />,
  error: <XCircle className="text-red-500" />,
  info: <Info className="text-blue-500" />,
};

const Toast: React.FC<{ notification: Notification }> = ({ notification }) => {
  const removeNotification = useAppStore((state) => state.removeNotification);
  
  const toastVariants = {
    initial: { opacity: 0, y: 50, scale: 0.5 },
    animate: { opacity: 1, y: 0, scale: 1 },
    exit: { opacity: 0, y: 20, scale: 0.5 },
  };

  return (
    <motion.div
      layout
      variants={toastVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
      className="mb-4 w-full max-w-sm bg-kai-surface border border-border-color rounded-lg shadow-2xl p-4 flex items-start gap-3"
    >
      <div className="flex-shrink-0">{icons[notification.type]}</div>
      <div className="flex-grow text-sm text-text-primary">{notification.message}</div>
      <button onClick={() => removeNotification(notification.id)} className="flex-shrink-0 text-text-secondary hover:text-text-primary">
        <X size={18} />
      </button>
    </motion.div>
  );
};

export const ToastContainer: React.FC = () => {
    const notifications = useAppStore((state) => state.notifications);

    return (
        <div className="fixed bottom-4 right-4 z-[100] flex flex-col items-end">
            <AnimatePresence>
                {notifications.map((n) => (
                    <Toast key={n.id} notification={n} />
                ))}
            </AnimatePresence>
        </div>
    )
}
