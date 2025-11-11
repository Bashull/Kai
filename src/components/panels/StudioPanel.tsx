import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Code, Image as ImageIcon, Terminal, Video, Scan } from 'lucide-react';
import CodePanel from './CodePanel';
import ImagePanel from './ImagePanel';
import ConsolePanel from './ConsolePanel';
const VideoPanel = React.lazy(() => import('./VideoPanel'));
const AnalysisPanel = React.lazy(() => import('./AnalysisPanel'));

type StudioTab = 'code' | 'image' | 'video' | 'analysis' | 'console';

const TABS: { id: StudioTab; label: string; icon: React.ElementType }[] = [
    { id: 'code', label: 'Código', icon: Code },
    { id: 'image', label: 'Imágenes', icon: ImageIcon },
    { id: 'video', label: 'Vídeo', icon: Video },
    { id: 'analysis', label: 'Análisis', icon: Scan },
    { id: 'console', label: 'Consola', icon: Terminal },
];

const StudioPanel: React.FC = () => {
    const [activeTab, setActiveTab] = useState<StudioTab>('code');

    const renderContent = () => {
        switch (activeTab) {
            case 'code': return <CodePanel />;
            case 'image': return <ImagePanel />;
            case 'video': return <VideoPanel />;
            case 'analysis': return <AnalysisPanel />;
            case 'console': return <ConsolePanel />;
            default: return null;
        }
    };
    
    const contentVariants = {
        initial: { opacity: 0, y: 20 },
        animate: { opacity: 1, y: 0 },
        exit: { opacity: 0, y: -20 },
    };

    return (
        <div className="flex flex-col h-full">
            <div className="flex-shrink-0">
                <h1 className="h1-title">IA Studio</h1>
                <p className="p-subtitle">Mi suite de herramientas multimodales para la creación y el diagnóstico.</p>
            </div>

            <div className="flex-shrink-0 border-b border-border-color my-4 overflow-x-auto">
                <nav className="-mb-px flex space-x-6" aria-label="Tabs">
                    {TABS.map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`${
                                activeTab === tab.id
                                    ? 'text-kai-primary'
                                    : 'text-text-secondary hover:text-text-primary'
                            } relative group inline-flex items-center py-3 px-1 border-b-2 border-transparent font-medium text-sm transition-colors whitespace-nowrap`}
                            aria-current={activeTab === tab.id ? 'page' : undefined}
                        >
                            <tab.icon className="-ml-0.5 mr-2 h-5 w-5" aria-hidden="true" />
                            <span>{tab.label}</span>
                             {activeTab === tab.id && (
                                <motion.div
                                    className="absolute bottom-[-1px] left-0 right-0 h-0.5 bg-kai-primary"
                                    layoutId="studio-tab-underline"
                                />
                            )}
                        </button>
                    ))}
                </nav>
            </div>

            <div className="flex-grow panel-container overflow-y-auto">
                 <AnimatePresence mode="wait">
                    <motion.div
                        key={activeTab}
                        variants={contentVariants}
                        initial="initial"
                        animate="animate"
                        exit="exit"
                        transition={{ duration: 0.2 }}
                        className="h-full"
                    >
                        <React.Suspense fallback={<div>Cargando...</div>}>
                          {renderContent()}
                        </React.Suspense>
                    </motion.div>
                </AnimatePresence>
            </div>
        </div>
    );
};

export default StudioPanel;
