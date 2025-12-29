import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';
import {
    MessageSquare, BrainCircuit, Flame, Bot, CheckSquare, Settings,
    FileText, Star, BookOpen, Camera, Search, Bell, Menu, X, Radio, Dna, UserSquare
} from 'lucide-react';
import KaiAvatar from '../ui/KaiAvatar';
import NotificationPopover from '../ui/NotificationPopover';
import { isToday } from 'date-fns';
import { Panel } from '../../types';

const navItems: { id: Panel; label: string; icon: React.ElementType }[] = [
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'live', label: 'Live', icon: Radio },
    { id: 'kernel', label: 'Kernel', icon: BrainCircuit },
    { id: 'evolution', label: 'Evolución', icon: Dna },
    { id: 'forge', label: 'La Forja', icon: Flame },
    { id: 'studio', label: 'IA Studio', icon: Bot },
    { id: 'tasks', label: 'Misiones', icon: CheckSquare },
    { id: 'resume', label: 'Constructor CV', icon: FileText },
    { id: 'avatars', label: 'Avatares', icon: UserSquare },
];

const secondaryNavItems: { id: Panel; label: string; icon: React.ElementType }[] = [
    { id: 'awesome', label: 'Recursos', icon: Star },
    { id: 'diary', label: 'Diario', icon: BookOpen },
    { id: 'snapshots', label: 'Snapshots', icon: Camera },
];

const NavButton: React.FC<{ item: { id: string, label: string, icon: React.ElementType }; isActive: boolean; isCollapsed: boolean; onClick: () => void; badgeCount?: number }> =
    ({ item, isActive, isCollapsed, onClick, badgeCount = 0 }) => {
        const spanVariants = {
            initial: { opacity: 0, width: 0 },
            animate: { opacity: 1, width: 'auto' },
            exit: { opacity: 0, width: 0 },
        };
        return (
            <button
                onClick={onClick}
                title={item.label}
                className={`flex items-center w-full text-sm font-medium rounded-lg transition-colors duration-200 ${
                    isActive
                        ? 'bg-kai-primary/20 text-text-primary'
                        : 'text-text-secondary hover:text-text-primary hover:bg-kai-surface'
                } ${isCollapsed ? 'justify-center h-12' : 'px-4 h-11'}`}
            >
                <item.icon className={`h-5 w-5 ${isCollapsed ? '' : 'mr-3'}`} />
                <AnimatePresence>
                    {!isCollapsed && (
                        <motion.span
                            variants={spanVariants}
                            initial="initial"
                            animate="animate"
                            exit="exit"
                            transition={{ duration: 0.2 }}
                            className="flex-1 text-left whitespace-nowrap"
                        >
                            {item.label}
                        </motion.span>
                    )}
                </AnimatePresence>
                 {badgeCount > 0 && (
                    <span className="bg-red-500 text-white text-xs rounded-full min-w-[1.25rem] h-5 flex items-center justify-center px-1">
                        {badgeCount}
                    </span>
                )}
            </button>
        );
    };

const Sidebar: React.FC = () => {
    const { 
        activePanel, 
        setActivePanel, 
        sidebarCollapsed, 
        toggleSidebar,
        searchQuery,
        setSearchQuery,
        executeSearch,
        tasks,
        showNotifications,
        toggleNotifications,
        isTyping,
        isSummarizing,
        isGeneratingCode,
        isGeneratingImages,
        isGeneratingVideo,
        isAnalyzing,
        isEditing,
        isSearching,
        isConnecting,
        isExtracting,
    } = useAppStore();

    const [dueTasks, setDueTasks] = useState<any[]>([]);

    useEffect(() => {
        const todayTasks = tasks.filter(task => task.dueDate && task.status === 'PENDING' && isToday(new Date(task.dueDate)));
        setDueTasks(todayTasks);
    }, [tasks]);

    const handleSearchSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        executeSearch();
    };

    const isKaiBusy = isTyping || isSummarizing || isGeneratingCode || isGeneratingImages || isSearching || isConnecting || isExtracting || isGeneratingVideo || isAnalyzing || isEditing;

    return (
        <aside
            className={`fixed top-0 left-0 h-full bg-kai-dark/50 backdrop-blur-lg border-r border-border-color z-40 flex flex-col transition-all duration-300 ease-in-out ${
                sidebarCollapsed ? 'w-20' : 'w-64'
            }`}
        >
            <div className={`flex items-center border-b border-border-color transition-all duration-300 ${sidebarCollapsed ? 'h-20 justify-center' : 'h-20 px-6'}`}>
                {sidebarCollapsed ? (
                     <button onClick={toggleSidebar} className="text-text-secondary hover:text-text-primary p-2">
                         <Menu/>
                    </button>
                ) : (
                    <div className="flex items-center justify-between w-full">
                        <div className="flex items-center gap-2">
                             <KaiAvatar size="sm" isBusy={isKaiBusy} />
                             <h1 className="text-xl font-bold font-orbitron">KaiOS</h1>
                        </div>
                        <button onClick={toggleSidebar} className="text-text-secondary hover:text-text-primary p-2">
                            <X size={20}/>
                        </button>
                    </div>
                )}
            </div>

            <div className="flex-1 flex flex-col p-4 space-y-4 overflow-y-auto">
                <form onSubmit={handleSearchSubmit}>
                    <div className="relative">
                         <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-secondary pointer-events-none" />
                         <input
                            type="text"
                            placeholder={sidebarCollapsed ? '' : "Buscar..."}
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className={`w-full form-input bg-kai-surface border-transparent focus:border-kai-primary transition-all ${sidebarCollapsed ? 'pl-10' : 'pl-10'}`}
                         />
                    </div>
                </form>
                
                <nav className="space-y-2">
                    {navItems.map(item => (
                        <NavButton
                            key={item.id}
                            item={item}
                            isActive={activePanel === item.id}
                            isCollapsed={sidebarCollapsed}
                            onClick={() => setActivePanel(item.id)}
                        />
                    ))}
                </nav>
                <div className="pt-2">
                    <h3 className={`text-xs font-semibold text-text-secondary uppercase tracking-wider ${sidebarCollapsed ? 'text-center' : 'px-4'}`}>
                        {sidebarCollapsed ? '·' : 'Memoria'}
                    </h3>
                    <nav className="space-y-2 mt-2">
                        {secondaryNavItems.map(item => (
                             <NavButton
                                key={item.id}
                                item={item}
                                isActive={activePanel === item.id}
                                isCollapsed={sidebarCollapsed}
                                onClick={() => setActivePanel(item.id)}
                            />
                        ))}
                    </nav>
                </div>
            </div>

            <div className="p-4 border-t border-border-color space-y-2">
                <NavButton
                    item={{ id: 'settings', label: 'Ajustes', icon: Settings }}
                    isActive={activePanel === 'settings'}
                    isCollapsed={sidebarCollapsed}
                    onClick={() => setActivePanel('settings' as Panel)}
                />
                 <div className="relative">
                    <NavButton
                        item={{ id: 'notifications', label: 'Notificaciones', icon: Bell }}
                        isActive={showNotifications}
                        isCollapsed={sidebarCollapsed}
                        onClick={toggleNotifications}
                        badgeCount={dueTasks.length}
                    />
                    <AnimatePresence>
                       {showNotifications && dueTasks.length > 0 && <NotificationPopover tasks={dueTasks} onClose={toggleNotifications} isSidebarCollapsed={sidebarCollapsed} />}
                    </AnimatePresence>
                </div>
            </div>
        </aside>
    );
};

export default Sidebar;
