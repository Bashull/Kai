import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
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
import AwesomeResourcesPanel from './components/panels/AwesomeResourcesPanel';
import DiaryPanel from './components/panels/DiaryPanel';
import SnapshotsPanel from './components/panels/SnapshotsPanel';
import KaiAvatar from './components/ui/KaiAvatar';
import { ToastContainer } from './components/ui/Toast';
import SearchResultsModal from './components/ui/SearchResultsModal';

const panelMap = {
  chat: ChatPanel,
  kernel: KernelPanel,
  forge: ForgePanel,
  studio: StudioPanel,
  tasks: TasksPanel,
  settings: SettingsPanel,
  resume: ResumeBuilderPanel,
  awesome: AwesomeResourcesPanel,
  diary: DiaryPanel,
  snapshots: SnapshotsPanel,
};

const App: React.FC = () => {
  const { activePanel, sidebarCollapsed, theme, setDueTasks, tasks } = useAppStore();

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'light') {
      root.classList.remove('dark');
    } else {
      root.classList.add('dark');
    }
  }, [theme]);

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
            <AnimatePresence mode="wait">
              <motion.div
                  key={activePanel}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3 }}
              >
                {PanelComponent ? <PanelComponent /> : <div>Panel not found</div>}
              </motion.div>
            </AnimatePresence>
        </div>
      </main>
      <KaiAvatar />
      <ToastContainer />
      <SearchResultsModal />
    </div>
  );
};

export default App;