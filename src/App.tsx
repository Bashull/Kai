import React from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useAppStore } from './store/useAppStore';
import Sidebar from './components/layout/Sidebar';
import ChatPanel from './components/panels/ChatPanel';
import SettingsPanel from './components/panels/SettingsPanel';
import KernelPanel from './components/panels/KernelPanel';
import ForgePanel from './components/panels/ForgePanel';
import StudioPanel from './components/panels/StudioPanel';
import KaiAvatar from './components/ui/KaiAvatar';

// Mapping of the main panels of the new architecture
const panels: { [key: string]: React.ComponentType } = {
  chat: ChatPanel,
  kernel: KernelPanel,
  forge: ForgePanel,
  studio: StudioPanel,
  settings: SettingsPanel,
};

const App: React.FC = () => {
  const { activePanel, sidebarCollapsed } = useAppStore((state) => ({
    activePanel: state.activePanel,
    sidebarCollapsed: state.sidebarCollapsed,
  }));

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
