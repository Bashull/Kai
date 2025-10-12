// FIX: Replaced the incorrect App component with the main application layout.
// This new component correctly integrates with the sidebar, panels, and useAppStore,
// resolving errors related to a missing default export and a missing function import.
import React, { useEffect } from 'react';
import { motion } from 'framer-motion';
import { parseISO } from 'date-fns';
import { useAppStore } from './store/useAppStore';
import Sidebar from './components/layout/Sidebar';

// Panel Imports
import ChatPanel from './components/panels/ChatPanel';
import KernelPanel from './components/panels/KernelPanel';
import ForgePanel from './components/panels/ForgePanel';
import StudioPanel from './components/panels/StudioPanel';
import TasksPanel from './components/panels/TasksPanel';
import SettingsPanel from './components/panels/SettingsPanel';
import ResumeBuilderPanel from './components/panels/ResumeBuilderPanel';
import KaiAvatar from './components/ui/KaiAvatar';

const panelMap = {
  chat: ChatPanel,
  kernel: KernelPanel,
  forge: ForgePanel,
  studio: StudioPanel,
  tasks: TasksPanel,
  settings: SettingsPanel,
  resume: ResumeBuilderPanel,
};

const App: React.FC = () => {
  const { activePanel, sidebarCollapsed, theme, setTheme, setDueTasks, tasks } = useAppStore();

  useEffect(() => {
    setTheme(theme); // Apply theme on initial load
  }, [setTheme, theme]);

  useEffect(() => {
    const now = new Date();
    const dueAndOverdue = tasks.filter(task => 
      task.status === 'PENDING' && task.dueDate && parseISO(task.dueDate) <= now
    );
    setDueTasks(dueAndOverdue);
  }, [tasks, setDueTasks]);

  const PanelComponent = panelMap[activePanel];

  return (
    <div className="flex h-screen bg-kai-dark text-text-primary font-sans overflow-hidden">
      <Sidebar />
      <motion.main
        className="flex-1 overflow-y-auto"
        animate={{ paddingLeft: sidebarCollapsed ? '4rem' : '16rem' }}
        transition={{ duration: 0.3, ease: 'easeInOut' }}
      >
        <div className="p-4 sm:p-8 max-w-7xl mx-auto">
            {PanelComponent ? <PanelComponent /> : <div>Panel not found</div>}
        </div>
      </motion.main>
      <KaiAvatar />
    </div>
  );
};

export default App;