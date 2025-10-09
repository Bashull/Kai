import React, { useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useAppStore } from './store/useAppStore';
import Sidebar from './components/layout/Sidebar';
import ChatPanel from './components/panels/ChatPanel';
import SettingsPanel from './components/panels/SettingsPanel';
import KernelPanel from './components/panels/KernelPanel';
import ForgePanel from './components/panels/ForgePanel';
import StudioPanel from './components/panels/StudioPanel';
import KaiAvatar from './components/ui/KaiAvatar';
import TasksPanel from './components/panels/TasksPanel';
import { differenceInHours, parseISO } from 'date-fns';

// Mapping of the main panels of the new architecture
const panels: { [key: string]: React.ComponentType } = {
  chat: ChatPanel,
  kernel: KernelPanel,
  forge: ForgePanel,
  studio: StudioPanel,
  tasks: TasksPanel,
  settings: SettingsPanel,
};

const App: React.FC = () => {
  const { activePanel, sidebarCollapsed, tasks, setDueTasks } = useAppStore((state) => ({
    activePanel: state.activePanel,
    sidebarCollapsed: state.sidebarCollapsed,
    tasks: state.tasks,
    setDueTasks: state.setDueTasks,
  }));

  // Effect to periodically check for tasks due within 24 hours
  useEffect(() => {
    const checkDueTasks = () => {
        const now = new Date();
        const upcomingTasks = tasks.filter(task => {
            if (task.status !== 'PENDING' || !task.dueDate) return false;
            try {
              const dueDate = parseISO(task.dueDate);
              const hoursUntilDue = differenceInHours(dueDate, now);
              // Check for tasks due in the next 24 hours but not past due
              return hoursUntilDue >= 0 && hoursUntilDue <= 24;
            } catch (error) {
              // Invalid date string
              return false;
            }
        });
        setDueTasks(upcomingTasks);
    };

    checkDueTasks(); // Initial check
    const intervalId = setInterval(checkDueTasks, 60 * 1000 * 5); // Check every 5 minutes

    return () => clearInterval(intervalId); // Cleanup on component unmount
  }, [tasks, setDueTasks]);


  const ActivePanelComponent = panels[activePanel];

  return (
    <div className="flex h-screen bg-gray-900 text-gray-200 font-sans">
      <Sidebar />
      <main
        className={`flex-1 flex flex-col transition-all duration-300 ease-in-out`}
        style={{ marginLeft: sidebarCollapsed ? '4rem' : '16rem' }}
      >
        <div className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={activePanel}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.2 }}
            >
              {ActivePanelComponent && <ActivePanelComponent />}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
      <KaiAvatar />
    </div>
  );
};

export default App;