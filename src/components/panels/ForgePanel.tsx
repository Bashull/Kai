import React from 'react';
import { useAppStore } from '../../store/useAppStore';
import { AnimatePresence, motion } from 'framer-motion';
import Button from '../ui/Button';
import { Flame, Cpu, ShieldCheck, FileCode } from 'lucide-react';
import TrainingJobStatusBadge from '../ui/TrainingJobStatusBadge';
import { formatRelativeTime } from '../../utils/helpers';
import { TrainingJob } from '../../types';
import { format } from 'date-fns';


const TrainingLogViewer: React.FC<{ logs: TrainingJob['logs'] }> = ({ logs }) => {
    if (!logs || logs.length === 0) {
        return <p className="text-xs text-text-secondary/70 italic">Esperando inicio del entrenamiento...</p>;
    }
    return (
        <div className="bg-black/40 rounded-lg p-3 mt-4 max-h-40 overflow-y-auto font-mono text-xs">
            {logs.map(log => (
                <div key={log.timestamp} className="flex items-start gap-2">
                    <span className="text-gray-500 shrink-0">{format(new Date(log.timestamp), 'HH:mm:ss')}</span>
                    <span className="text-gray-300 whitespace-pre-wrap">{log.message}</span>
                </div>
            ))}
        </div>
    );
};


const ForgePanel: React.FC = () => {
    const { trainingJobs, addTrainingJob, entities } = useAppStore(state => ({
        trainingJobs: state.trainingJobs,
        addTrainingJob: state.addTrainingJob,
        entities: state.entities,
    }));
    
    const integratedEntitiesCount = entities.filter(e => e.status === 'INTEGRATED').length;
    const isTraining = trainingJobs.some(j => j.status === 'TRAINING' || j.status === 'QUEUED');

    const handleStartTraining = () => {
        if (isTraining || integratedEntitiesCount === 0) return;
        addTrainingJob({
            modelName: `kai-os-v3.${Date.now()}`,
            description: `Fine-tuning con ${integratedEntitiesCount} nuevas entidades integradas.`,
        });
    };
    
    return (
    <div>
        <h1 className="h1-title">La Forja</h1>
        <p className="p-subtitle">Mi motor de evolución y entrenamiento de modelos, conectado a `autotrain-forge`.</p>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Control Panel */}
            <div className="lg:col-span-1">
                 <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    className="panel-container sticky top-8 space-y-6"
                  >
                    <div className="flex items-center gap-3">
                        <Flame className="w-6 h-6 text-orange-500" />
                        <h2 className="text-xl font-bold">Control de Entrenamiento</h2>
                    </div>

                    <div className="space-y-3 text-sm">
                        <div className="flex justify-between items-center">
                            <span className="text-text-secondary font-medium flex items-center gap-2"><Cpu size={16}/>autotrain-forge</span>
                            <span className="font-bold text-green-400">CONECTADO</span>
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="text-text-secondary font-medium flex items-center gap-2"><ShieldCheck size={16}/>Entidades Listas</span>
                            <span className="font-bold text-kai-primary">{integratedEntitiesCount}</span>
                        </div>
                    </div>
                    
                    <Button 
                        onClick={handleStartTraining} 
                        disabled={isTraining || integratedEntitiesCount === 0}
                        className="w-full"
                        variant="kai"
                    >
                        {isTraining ? 'Entrenamiento en Progreso...' : 'Iniciar Nuevo Fine-Tuning'}
                    </Button>
                     {integratedEntitiesCount === 0 && !isTraining &&
                        <p className="text-xs text-center text-text-secondary/70">
                            No hay nuevas entidades integradas en el Kernel para entrenar.
                        </p>
                     }
                  </motion.div>
            </div>
            {/* Training Jobs Log */}
            <div className="lg:col-span-2">
                 <h2 className="text-xl font-bold mb-4">Registro de Trabajos de la Forja</h2>
                 <div className="space-y-4 max-h-[calc(100vh-20rem)] overflow-y-auto pr-2">
                    <AnimatePresence>
                        {!trainingJobs.length && (
                             <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                className="text-center py-16 text-gray-500"
                            >
                                <p>La Forja está inactiva. Inicia un trabajo de entrenamiento.</p>
                            </motion.div>
                        )}
                        {trainingJobs.map(job => (
                             <motion.div
                                key={job.id}
                                layout
                                initial={{ opacity: 0, y: 50, scale: 0.3 }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.5, transition: { duration: 0.2 } }}
                                transition={{ type: 'spring', stiffness: 500, damping: 50, mass: 0.7 }}
                                className="bg-kai-surface/50 border border-border-color rounded-lg p-4 transition-all duration-200 hover:bg-kai-surface"
                            >
                                <div className="flex justify-between items-start gap-4">
                                    <div>
                                        <h3 className="font-bold text-text-primary">{job.modelName}</h3>
                                        <p className="text-sm text-text-secondary mt-1">{job.description}</p>
                                    </div>
                                    <TrainingJobStatusBadge status={job.status} />
                                </div>
                                <div className="text-xs text-text-secondary/60 mt-3 flex justify-between items-center">
                                     <div className="flex items-center gap-2">
                                        <FileCode size={14}/>
                                        <span>Registro de Entrenamiento</span>
                                     </div>
                                    <span>Iniciado {formatRelativeTime(job.createdAt)}</span>
                                </div>
                                {(job.status === 'TRAINING' || job.status === 'COMPLETED' || job.status === 'FAILED') && (
                                    <TrainingLogViewer logs={job.logs} />
                                )}
                            </motion.div>
                        ))}
                    </AnimatePresence>
                 </div>
            </div>
        </div>
    </div>
    );
};
export default ForgePanel;