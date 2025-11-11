import React, { useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Task } from '../../types';
import { useAppStore } from '../../store/useAppStore';
import { formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';
import { Bell, Clock } from 'lucide-react';

interface NotificationPopoverProps {
    tasks: Task[];
    onClose: () => void;
    isSidebarCollapsed: boolean;
}

const NotificationPopover: React.FC<NotificationPopoverProps> = ({ tasks, onClose, isSidebarCollapsed }) => {
    const popoverRef = useRef<HTMLDivElement>(null);
    const { setActivePanel } = useAppStore();

    // Effect to handle clicks outside the popover to close it
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
                const sidebarButton = (event.target as Element).closest('[title="Notificaciones"]');
                if (!sidebarButton) {
                   onClose();
                }
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [onClose]);

    const handleTaskClick = () => {
        setActivePanel('tasks');
        onClose();
    };

    const popoverVariants = {
        hidden: { opacity: 0, y: -10, scale: 0.95 },
        visible: { opacity: 1, y: 0, scale: 1 },
    };

    const positionClasses = isSidebarCollapsed
        ? 'left-[4.5rem] bottom-20' // Position when sidebar is collapsed
        : 'left-4 bottom-20'; // Position when sidebar is open

    return (
        <motion.div
            ref={popoverRef}
            variants={popoverVariants}
            initial="hidden"
            animate="visible"
            exit="hidden"
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className={`absolute ${positionClasses} w-72 bg-kai-surface border border-border-color rounded-lg shadow-2xl z-30`}
        >
            <div className="p-3 border-b border-border-color flex items-center gap-2">
                <Bell size={16} className="text-kai-primary" />
                <h3 className="font-semibold text-sm">Tareas Próximas a Vencer</h3>
            </div>
            <ul className="py-2 max-h-60 overflow-y-auto">
                {tasks.map(task => (
                    <li key={task.id}>
                        <a
                            href="#"
                            onClick={(e) => { e.preventDefault(); handleTaskClick(); }}
                            className="block px-3 py-2 text-sm hover:bg-kai-dark/50 group"
                        >
                            <p className="font-medium text-text-primary truncate group-hover:text-white">{task.title}</p>
                            <p className="text-xs text-kai-primary flex items-center gap-1 mt-1">
                                <Clock size={12} />
                                {task.dueDate && <span>Vence {formatDistanceToNow(new Date(task.dueDate), { locale: es, addSuffix: true })}</span>}
                            </p>
                        </a>
                    </li>
                ))}
            </ul>
        </motion.div>
    );
};

export default NotificationPopover;
