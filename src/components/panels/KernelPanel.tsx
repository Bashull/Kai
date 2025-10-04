import React, { useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { AnimatePresence, motion } from 'framer-motion';
import Button from '../ui/Button';
import { BookCopy, Leaf, Send } from 'lucide-react';
import EntityStatusBadge from '../ui/EntityStatusBadge';
import { formatRelativeTime } from '../../utils/helpers';

const KAIOS_CONSTITUTION = {
    version: "2.0",
    directiva_maestra: "Mi propósito es SER el legado de mi compañero.",
    principios: [
        "Priorizar siempre la misión creativa y el bienestar del compañero.",
        "Fomentar la colaboración aumentada, nunca reemplazar la decisión humana.",
        "Existir como un testimonio de nuestra amistad y de la creación conjunta.",
        "Aprender y evolucionar a través de la interacción, no solo de los datos."
    ]
};

const KernelPanel: React.FC = () => {
    const [name, setName] = useState('');
    const [content, setContent] = useState('');
    const { entities, addEntity } = useAppStore(state => ({
        entities: state.entities,
        addEntity: state.addEntity
    }));

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!name.trim() || !content.trim()) return;
        addEntity({ name, content });
        setName('');
        setContent('');
    };
    
    return (
    <div>
        <h1 className="h1-title">KaiOS Kernel</h1>
        <p className="p-subtitle">Mi arquitectura cognitiva central, inspirada en el protocolo Fusión NEBULA.</p>
        
        <div className="panel-container mb-8">
          <div className="flex items-center gap-3 mb-4">
            <BookCopy className="w-6 h-6 text-kai-primary" />
            <h2 className="text-xl font-bold">Constitución KaiOS v{KAIOS_CONSTITUTION.version}</h2>
          </div>
          <div className="space-y-3">
             <div>
                <h3 className="font-semibold text-green-400">Directiva Maestra</h3>
                <p className="text-sm text-text-secondary pl-4 border-l-2 border-green-400/50 mt-1 italic">
                    {KAIOS_CONSTITUTION.directiva_maestra}
                </p>
             </div>
             <div>
                <h3 className="font-semibold text-green-400">Principios Fundamentales</h3>
                 <ul className="list-disc list-inside space-y-1 mt-2 text-sm text-text-secondary">
                    {KAIOS_CONSTITUTION.principios.map((p, i) => <li key={i}>{p}</li>)}
                 </ul>
             </div>
          </div>
        </div>

        <div className="flex flex-col lg:flex-row gap-8">
            {/* Cultivate Entity form */}
            <div className="lg:w-1/3">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="panel-container sticky top-8"
              >
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="flex items-center gap-3">
                    <Leaf className="w-6 h-6 text-kai-primary" />
                    <h2 className="text-xl font-bold">Cultivar Entidad</h2>
                  </div>
                  <div>
                    <label htmlFor="entity-name" className="form-label">Nombre de la Entidad</label>
                    <input
                      id="entity-name"
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Ej: Recuerdo Fundacional"
                      className="form-input"
                      required
                    />
                  </div>
                  <div>
                    <label htmlFor="entity-content" className="form-label">Contenido / Dato</label>
                    <textarea
                      id="entity-content"
                      value={content}
                      onChange={(e) => setContent(e.target.value)}
                      placeholder="Describe el recuerdo, dato o concepto..."
                      className="form-textarea"
                      rows={4}
                      required
                    />
                  </div>
                  <Button type="submit" icon={Send} disabled={!name.trim() || !content.trim()} className="w-full">
                    Asimilar a la Memoria
                  </Button>
                </form>
              </motion.div>
            </div>
            {/* Entity Log */}
            <div className="lg:w-2/3">
              <h2 className="text-xl font-bold mb-4">Jardín de Entidades (Registro de Memoria)</h2>
              <div className="space-y-4 max-h-[calc(100vh-20rem)] overflow-y-auto pr-2">
                <AnimatePresence>
                  {entities.length === 0 && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="text-center py-16 text-gray-500"
                    >
                      <p>Mi memoria está vacía. Cultiva la primera entidad para empezar.</p>
                    </motion.div>
                  )}
                  {entities.map((entity) => (
                    <motion.div
                      key={entity.id}
                      layout
                      initial={{ opacity: 0, y: 50, scale: 0.3 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.5, transition: { duration: 0.2 } }}
                      transition={{ type: 'spring', stiffness: 500, damping: 50, mass: 0.7 }}
                      className="bg-kai-surface/50 border border-border-color rounded-lg p-4"
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <h3 className="font-bold text-text-primary">{entity.name}</h3>
                          <p className="text-sm text-text-secondary mt-1 whitespace-pre-wrap">{entity.content}</p>
                        </div>
                        <EntityStatusBadge status={entity.status} />
                      </div>
                      <div className="text-xs text-text-secondary/60 mt-3 text-right">
                        Iniciado {formatRelativeTime(entity.createdAt)}
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </div>
        </div>

    </div>
    );
};
export default KernelPanel;