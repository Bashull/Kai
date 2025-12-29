import React, { useEffect } from 'react';
import { useAppStore } from './store/useAppStore';
import { AnimatePresence, motion } from 'framer-motion';

// Layout & UI
import Sidebar from './components/layout/Sidebar';
import DynamicBackground from './components/ui/DynamicBackground';
import CustomCursor from './components/ui/CustomCursor';
import { ToastContainer } from './components/ui/Toast';
import SearchResultsModal from './components/ui/SearchResultsModal';

// Panels
import ChatPanel from './components/panels/ChatPanel';
import LivePanel from './components/panels/LivePanel';
import KernelPanel from './components/panels/KernelPanel';
import ForgePanel from './components/panels/ForgePanel';
import StudioPanel from './components/panels/StudioPanel';
import TasksPanel from './components/panels/TasksPanel';
import SettingsPanel from './components/panels/SettingsPanel';
import ResumeBuilderPanel from './components/panels/ResumeBuilderPanel';
import AwesomeResourcesPanel from './components/panels/AwesomeResourcesPanel';
import DiaryPanel from './components/panels/DiaryPanel';
import SnapshotsPanel from './components/panels/SnapshotsPanel';
import EvolutionPanel from './components/panels/EvolutionPanel';
import AvatarsPanel from './components/panels/AvatarsPanel';
import { Panel } from './types';

// Lazy load panels that might be heavy
const VideoPanel = React.lazy(() => import('./components/panels/VideoPanel'));
const AnalysisPanel = React.lazy(() => import('./components/panels/AnalysisPanel'));


const panelComponents: { [key in Panel]: React.FC | React.LazyExoticComponent<React.FC<{}>> } = {
  chat: ChatPanel,
  live: LivePanel,
  kernel: KernelPanel,
  forge: ForgePanel,
  studio: StudioPanel,
  tasks: TasksPanel,
  settings: SettingsPanel,
  resume: ResumeBuilderPanel,
  awesome: AwesomeResourcesPanel,
  diary: DiaryPanel,
  snapshots: SnapshotsPanel,
  evolution: EvolutionPanel,
  avatars: AvatarsPanel,
  video: VideoPanel,
  analysis: AnalysisPanel,
};

const App: React.FC = () => {
  const { activePanel, theme, sidebarCollapsed, pollJobs } = useAppStore();

  useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(`${theme}`);
  }, [theme]);

  useEffect(() => {
    const intervalId = setInterval(() => { pollJobs(); }, 5000);
    return () => clearInterval(intervalId);
  }, [pollJobs]);
  
  const ActivePanelComponent = panelComponents[activePanel];

  const panelVariants = {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -20 },
  };

  return (
    <div className="font-sans bg-kai-dark text-text-primary min-h-screen flex">
      <DynamicBackground />
      <CustomCursor />
      
      <Sidebar />
      
      <main className={`flex-1 transition-all duration-300 ease-in-out ${sidebarCollapsed ? 'pl-20' : 'pl-64'}`}>
        <div className="p-4 sm:p-6 lg:p-8 h-screen overflow-y-auto">
            <AnimatePresence mode="wait">
                 <motion.div
                    key={activePanel}
                    variants={panelVariants}
                    initial="initial"
                    animate="animate"
                    exit="exit"
                    transition={{ duration: 0.3 }}
                    className="h-full"
                 >
                    <React.Suspense fallback={<div>Loading...</div>}>
                        {ActivePanelComponent && <ActivePanelComponent />}
                    </React.Suspense>
                 </motion.div>
            </AnimatePresence>
        </div>
      </main>

      <ToastContainer />
      <SearchResultsModal />
    </div>
  );
};

export default App;
