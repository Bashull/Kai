import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageSquare, BrainCircuit, Flame, Terminal, Settings, ChevronsLeft, ChevronsRight, CheckSquare, Bell, ClipboardList } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import { Panel } from '../../types';
import Button from '../ui/Button';
import NotificationPopover from '../ui/NotificationPopover';

// Navigation items for the new Genesis Architecture
const navItems: { panel: Panel; icon: React.ElementType; label: string }[] = [
  { panel: 'chat', icon: MessageSquare, label: 'Chat' },
  { panel: 'kernel', icon: BrainCircuit, label: 'Kernel' },
  { panel: 'forge', icon: Flame, label: 'La Forja' },
  { panel: 'studio', icon: Terminal, label: 'IA Studio' },
  { panel: 'tasks', icon: CheckSquare, label: 'Misiones' },
  { panel: 'resume', icon: ClipboardList, label: 'Constructor de CV' },
  { panel: 'settings', icon: Settings, label: 'Ajustes' },
];

const Sidebar: React.FC = () => {
  const { 
    activePanel, 
    setActivePanel, 
    sidebarCollapsed, 
    toggleSidebar,
    dueTasks,
    showNotifications,
    toggleNotifications,
  } = useAppStore();

  const sidebarVariants = {
    open: { width: '16rem' },
    closed: { width: '4rem' },
  };

  return (
    <motion.aside
      aria-label="Sidebar"
      animate={sidebarCollapsed ? 'closed' : 'open'}
      variants={sidebarVariants}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
      className="bg-gray-950/70 backdrop-blur-xl border-r border-border-color/50 h-screen flex flex-col fixed left-0 top-0 z-20"
    >
      <div className={`flex items-center ${sidebarCollapsed ? 'justify-center' : 'px-4'} h-16 border-b border-border-color/50`}>
        <motion.div
            animate={{ rotate: sidebarCollapsed ? 0 : 360 }}
            transition={{ duration: 0.5 }}
        >
            <span className="text-2xl" aria-hidden="true">🤖</span>
        </motion.div>
        {!sidebarCollapsed && <span className="text-xl font-bold ml-2 font-orbitron">KaiOS</span>}
      </div>
      <nav className="flex-1 px-2 py-4 space-y-2">
        {navItems.map(({ panel, icon: Icon, label }) => (
          <Button
            key={panel}
            variant={activePanel === panel ? 'secondary' : 'ghost'}
            onClick={() => setActivePanel(panel)}
            className={`w-full !justify-start !text-sm relative ${sidebarCollapsed ? '!px-2 !justify-center' : '!px-2'}`}
            title={label}
            aria-current={activePanel === panel ? 'page' : undefined}
          >
            {activePanel === panel && (
                <motion.div 
                    layoutId="sidebar-active-indicator"
                    className="absolute left-0 top-0 bottom-0 w-1 bg-kai-green rounded-r-full"
                />
            )}
            <Icon className="h-5 w-5" />
            {!sidebarCollapsed && <span className="ml-3">{label}</span>}
          </Button>
        ))}
      </nav>
      <div className="px-2 py-4 border-t border-border-color/50 space-y-2">
        <div className="relative">
            <Button
              variant="ghost"
              onClick={toggleNotifications}
              className={`w-full !justify-start !text-sm ${sidebarCollapsed ? '!px-2 !justify-center' : '!px-2'}`}
              title="Notificaciones"
            >
              <Bell className="h-5 w-5" />
              {!sidebarCollapsed && <span className="ml-3">Notificaciones</span>}
              {dueTasks.length > 0 && (
                 <span className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-white text-[10px] font-bold">
                    {dueTasks.length}
                </span>
              )}
            </Button>
            <AnimatePresence>
                {showNotifications && dueTasks.length > 0 && (
                    <NotificationPopover
                        tasks={dueTasks}
                        onClose={toggleNotifications}
                        isSidebarCollapsed={sidebarCollapsed}
                    />
                )}
            </AnimatePresence>
        </div>
        <Button
          variant="ghost"
          onClick={toggleSidebar}
          className={`w-full !justify-start !text-sm ${sidebarCollapsed ? '!px-2 !justify-center' : '!px-2'}`}
          title={sidebarCollapsed ? "Expandir Barra Lateral" : "Contraer Barra Lateral"}
          aria-label={sidebarCollapsed ? "Expandir Barra Lateral" : "Contraer Barra Lateral"}
        >
          {sidebarCollapsed ? <ChevronsRight className="h-5 w-5" /> : <ChevronsLeft className="h-5 w-5" />}
          {!sidebarCollapsed && <span className="ml-3">Contraer</span>}
        </Button>
      </div>
    </motion.aside>
  );
};

export default Sidebar;
