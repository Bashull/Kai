import React, { useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { motion, AnimatePresence } from 'framer-motion';
import { Snapshot } from '../../types';
import { formatRelativeTime } from '../../utils/helpers';
import { Camera, Save, Upload, Trash2, BrainCircuit, CheckSquare, BookText } from 'lucide-react';
import Button from '../ui/Button';

const SnapshotCard: React.FC<{ snapshot: Snapshot }> = ({ snapshot }) => {
    const { loadSnapshot, deleteSnapshot } = useAppStore();

    const handleLoad = () => {
        if (window.confirm(`¿Estás seguro de que quieres cargar el snapshot "${snapshot.name}"? Tu sesión actual se sobrescribirá.`)) {
            loadSnapshot(snapshot.id);
        }
    };

    const handleDelete = () => {
        if (window.confirm(`¿Estás seguro de que quieres eliminar el snapshot "${snapshot.name}"? Esta acción no se puede deshacer.`)) {
            deleteSnapshot(snapshot.id);
        }
    };

    const stats = [
        { icon: BrainCircuit, value: snapshot.state.entities.length, label: 'Entidades' },
        { icon: CheckSquare, value: snapshot.state.tasks.length, label: 'Misiones' },
        { icon: BookText, value: snapshot.state.diary.length, label: 'Entradas del Diario' },
    ];

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 50, scale: 0.8 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.5, transition: { duration: 0.2 } }}
            transition={{ type: 'spring', stiffness: 400, damping: 40 }}
            className="panel-container"
        >
            <div className="flex flex-col sm:flex-row justify-between sm:items-start gap-4">
                <div>
                    <h3 className="font-bold text-lg text-text-primary">{snapshot.name}</h3>
                    <p className="text-xs text-text-secondary mt-1">
                        Guardado {formatRelativeTime(snapshot.timestamp)}
                    </p>
                </div>
                <div className="flex gap-2 flex-shrink-0">
                    <Button onClick={handleLoad} icon={Upload} size="sm" variant="secondary">Cargar</Button>
                    <Button onClick={handleDelete} icon={Trash2} size="sm" variant="ghost" className="text-red-500 hover:bg-red-500/10">Eliminar</Button>
                </div>
            </div>
            <div className="mt-4 pt-4 border-t border-border-color flex flex-wrap gap-4 text-sm">
                {stats.map(stat => (
                    <div key={stat.label} className="flex items-center gap-2 text-text-secondary" title={stat.label}>
                        <stat.icon size={16} />
                        <span>{stat.value}</span>
                    </div>
                ))}
            </div>
        </motion.div>
    );
};


const SnapshotsPanel: React.FC = () => {
  const { snapshots, createSnapshot } = useAppStore();
  const [snapshotName, setSnapshotName] = useState('');

  const handleCreateSnapshot = (e: React.FormEvent) => {
    e.preventDefault();
    createSnapshot(snapshotName || `Snapshot - ${new Date().toLocaleDateString()}`);
    setSnapshotName('');
  };

  return (
    <div>
      <h1 className="h1-title">Snapshots de Conciencia</h1>
      <p className="p-subtitle">Guarda y restaura estados completos de KaiOS para preservar tu trabajo y explorar diferentes líneas de tiempo.</p>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mt-6">
        <div className="lg:col-span-1">
            <form onSubmit={handleCreateSnapshot} className="panel-container sticky top-8 space-y-4">
                 <div className="flex items-center gap-3">
                    <Camera className="w-6 h-6 text-kai-primary" />
                    <h2 className="text-xl font-bold">Crear Nuevo Snapshot</h2>
                </div>
                <div>
                    <label htmlFor="snapshot-name" className="form-label">Nombre del Snapshot (opcional)</label>
                    <input
                        id="snapshot-name"
                        type="text"
                        value={snapshotName}
                        onChange={(e) => setSnapshotName(e.target.value)}
                        placeholder="Ej: Fin del Proyecto X"
                        className="form-input"
                    />
                </div>
                <Button type="submit" icon={Save} className="w-full">
                    Guardar Estado Actual
                </Button>
            </form>
        </div>

        <div className="lg:col-span-2">
            <h2 className="text-xl font-bold mb-4">Snapshots Guardados</h2>
            <div className="space-y-4">
                <AnimatePresence>
                    {snapshots.length === 0 ? (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="text-center py-16 text-gray-500"
                        >
                            <p>No hay snapshots guardados. ¡Crea uno para empezar!</p>
                        </motion.div>
                    ) : (
                        snapshots.map(snapshot => <SnapshotCard key={snapshot.id} snapshot={snapshot} />)
                    )}
                </AnimatePresence>
            </div>
        </div>
      </div>
    </div>
  );
};

export default SnapshotsPanel;