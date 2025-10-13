import React, { useState, useEffect } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { AnimatePresence, motion } from 'framer-motion';
import Button from '../ui/Button';
import { BrainCircuit, Link, FileText, Type as TypeIcon, BookOpen, Edit, Save, Plus, Trash2, History, FileUp, Search } from 'lucide-react';
import { Entity, EntityType, Constitution } from '../../types';
import EntityStatusBadge from '../ui/EntityStatusBadge';
import { formatRelativeTime } from '../../utils/helpers';
import { format } from 'date-fns';

const EntityCard: React.FC<{ entity: Entity }> = ({ entity }) => {
    const iconMap = {
        TEXT: <TypeIcon size={16} />,
        URL: <Link size={16} />,
        DOCUMENT: <FileText size={16} />,
    };

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 50, scale: 0.3 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.5, transition: { duration: 0.2 } }}
            transition={{ type: 'spring', stiffness: 500, damping: 50, mass: 0.7 }}
            className="bg-kai-surface/50 border border-border-color rounded-lg p-4 transition-colors duration-200 hover:bg-kai-surface"
        >
            <div className="flex justify-between items-start gap-4">
                <div className="flex-grow">
                    <div className="flex items-center gap-2 text-text-secondary text-sm mb-2">
                        {iconMap[entity.type]}
                        <span>{entity.type}</span>
                    </div>
                    <p className="text-text-primary break-all line-clamp-3">{entity.content}</p>
                </div>
                <EntityStatusBadge status={entity.status} />
            </div>
            <div className="text-xs text-text-secondary/60 mt-3 text-right">
                Asimilado {formatRelativeTime(entity.createdAt)}
            </div>
        </motion.div>
    );
};


const KernelPanel: React.FC = () => {
    // Entity State
    const { entities, addEntity, isUploading } = useAppStore(state => ({
        entities: state.entities,
        addEntity: state.addEntity,
        isUploading: state.isUploading,
    }));
    const [content, setContent] = useState('');
    const [type, setType] = useState<EntityType>('TEXT');
    const [file, setFile] = useState<File | null>(null);

     // Search state and actions
    const { searchQuery, setSearchQuery, executeSearch } = useAppStore();

    const handleSearchSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        executeSearch();
    };

    const handleEntitySubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (type === 'DOCUMENT') {
            if (file) {
                addEntity({ content: file.name, type, source: 'File Upload', fileName: file.name });
                setFile(null);
            }
        } else {
            if(!content.trim()) return;
            addEntity({ content, type, source: 'Manual Input' });
            setContent('');
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
        }
    };


    // Constitution State
    const { constitution, versionHistory, updateConstitution, revertToVersion } = useAppStore();
    const [isEditing, setIsEditing] = useState(false);
    const [editableConstitution, setEditableConstitution] = useState<Constitution>(constitution);

    useEffect(() => {
        setEditableConstitution(constitution);
    }, [constitution]);

    const handlePrincipleChange = (index: number, value: string) => {
        const newPrinciples = [...editableConstitution.principles];
        newPrinciples[index] = value;
        setEditableConstitution({ ...editableConstitution, principles: newPrinciples });
    };
    
    const handleAddPrinciple = () => {
        setEditableConstitution({ ...editableConstitution, principles: [...editableConstitution.principles, ''] });
    };

    const handleRemovePrinciple = (index: number) => {
        const newPrinciples = editableConstitution.principles.filter((_, i) => i !== index);
        setEditableConstitution({ ...editableConstitution, principles: newPrinciples });
    };
    
    const handleSaveChanges = () => {
        updateConstitution(editableConstitution);
        setIsEditing(false);
    };

    const handleCancel = () => {
        setEditableConstitution(constitution);
        setIsEditing(false);
    };

    const handleRevert = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const version = parseInt(e.target.value, 10);
        if (version && confirm('¿Estás seguro de que quieres revertir a esta versión? Los cambios actuales se guardarán como una nueva versión.')) {
            revertToVersion(version);
        }
    };


    return (
        <div>
            <h1 className="h1-title">Kernel</h1>
            <p className="p-subtitle">Mi memoria central, base de conocimientos y principios fundamentales.</p>
            
            <div className="mt-8 space-y-12">
                {/* Search Section */}
                <section>
                    <div className="panel-container">
                        <div className="flex items-center gap-3 mb-4">
                            <Search className="w-6 h-6 text-kai-primary" />
                            <h2 className="text-xl font-bold">Buscar en el Kernel</h2>
                        </div>
                        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-2">
                            <div className="relative flex-grow">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-secondary pointer-events-none" />
                                <input
                                    type="text"
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    placeholder="Pregúntale al Kernel sobre tus datos..."
                                    className="form-input w-full pl-10"
                                />
                            </div>
                            <Button type="submit" className="w-full sm:w-auto">Buscar</Button>
                        </form>
                    </div>
                </section>

                {/* Constitution Section */}
                <section>
                    <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4 mb-4">
                        <div className="flex items-center gap-3">
                            <BookOpen className="w-6 h-6 text-green-400" />
                            <h2 className="text-xl font-bold">Constitución de Kai</h2>
                        </div>
                        {!isEditing ? (
                             <div className="flex items-center gap-4">
                                <div className="flex items-center gap-2">
                                     <History size={16} className="text-text-secondary"/>
                                     <select onChange={handleRevert} className="form-select !py-1 !text-xs" value="">
                                        <option value="">Ver Historial (V{versionHistory.length > 0 ? versionHistory[0].version : 0})</option>
                                        {versionHistory.map(v => (
                                            <option key={v.version} value={v.version}>
                                                V{v.version} - {format(new Date(v.date), 'dd MMM yyyy, HH:mm')}
                                            </option>
                                        ))}
                                     </select>
                                </div>
                                <Button onClick={() => setIsEditing(true)} icon={Edit} size="sm">Editar</Button>
                            </div>
                        ) : (
                             <div className="flex items-center gap-2">
                                <Button onClick={handleSaveChanges} icon={Save} size="sm" variant="success">Guardar Cambios</Button>
                                <Button onClick={handleCancel} size="sm" variant="secondary">Cancelar</Button>
                            </div>
                        )}
                       
                    </div>

                    <div className="panel-container space-y-6">
                        <div>
                            <label className="text-sm font-semibold text-text-secondary uppercase tracking-wider">Directiva Maestra</label>
                            {isEditing ? (
                                <textarea 
                                    value={editableConstitution.masterDirective}
                                    onChange={(e) => setEditableConstitution({...editableConstitution, masterDirective: e.target.value})}
                                    className="form-textarea mt-1 w-full"
                                    rows={3}
                                />
                            ) : (
                                <p className="text-text-primary mt-2">{constitution.masterDirective}</p>
                            )}
                        </div>
                        <div>
                            <label className="text-sm font-semibold text-text-secondary uppercase tracking-wider">Principios</label>
                            <ul className="space-y-4 mt-2">
                                {editableConstitution.principles.map((p, i) => (
                                    <li key={i} className="flex items-start gap-3">
                                        <span className="text-kai-primary font-bold mt-1">{i + 1}.</span>
                                        {isEditing ? (
                                             <div className="flex-grow flex items-center gap-2">
                                                <input 
                                                    type="text"
                                                    value={p}
                                                    onChange={(e) => handlePrincipleChange(i, e.target.value)}
                                                    className="form-input w-full !py-1"
                                                />
                                                <Button onClick={() => handleRemovePrinciple(i)} variant="ghost" size="sm" className="!p-1.5" aria-label="Eliminar principio">
                                                    <Trash2 size={16}/>
                                                </Button>
                                            </div>
                                        ) : (
                                            <p className="text-text-primary flex-grow">{p}</p>
                                        )}
                                    </li>
                                ))}
                            </ul>
                            {isEditing && (
                                <Button onClick={handleAddPrinciple} icon={Plus} size="sm" variant="secondary" className="mt-4">
                                    Añadir Principio
                                </Button>
                            )}
                        </div>
                    </div>
                </section>

                {/* Entity Assimilation Section */}
                <section>
                     <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        {/* Input Panel */}
                        <div className="lg:col-span-1">
                            <div className="panel-container sticky top-8">
                                <div className="flex items-center gap-3 mb-4">
                                    <BrainCircuit className="w-6 h-6 text-kai-primary" />
                                    <h2 className="text-xl font-bold">Asimilar Entidad</h2>
                                </div>
                                <form onSubmit={handleEntitySubmit} className="space-y-4">
                                    <div>
                                        <label className="form-label">Tipo de Entidad</label>
                                        <select value={type} onChange={e => { setType(e.target.value as EntityType); setFile(null); setContent(''); }} className="form-select">
                                            <option value="TEXT">Texto</option>
                                            <option value="URL">URL</option>
                                            <option value="DOCUMENT">Documento</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="form-label">Contenido</label>
                                        {type === 'DOCUMENT' ? (
                                            <label htmlFor="file-upload" className="file-dropzone">
                                                <div className="flex flex-col items-center justify-center pt-5 pb-6 text-center">
                                                    <FileUp className="w-8 h-8 mb-3 text-gray-400" />
                                                    {file ? (
                                                        <p className="text-sm text-gray-400"><span className="font-semibold">{file.name}</span> seleccionado</p>
                                                    ) : (
                                                        <>
                                                        <p className="mb-2 text-sm text-gray-400">
                                                            <span className="font-semibold">Haz clic para subir</span> o arrastra y suelta
                                                        </p>
                                                        <p className="text-xs text-gray-500">PDF, DOCX, TXT, etc.</p>
                                                        </>
                                                    )}
                                                </div>
                                                <input id="file-upload" type="file" className="hidden" onChange={handleFileChange} />
                                            </label>
                                        ) : (
                                            <textarea 
                                                value={content}
                                                onChange={e => setContent(e.target.value)}
                                                placeholder={type === 'URL' ? 'https://...' : 'Ingresa texto o referencia...'}
                                                className="form-textarea"
                                                rows={5}
                                            />
                                        )}
                                    </div>
                                    <Button type="submit" className="w-full" disabled={isUploading || (type === 'DOCUMENT' ? !file : !content.trim())} loading={isUploading}>
                                        {isUploading ? 'Asimilando...' : 'Asimilar en el Kernel'}
                                    </Button>
                                </form>
                            </div>
                        </div>

                        {/* Entities Log */}
                        <div className="lg:col-span-2">
                            <h2 className="text-xl font-bold mb-4">Registro de Entidades</h2>
                            <div className="space-y-4 max-h-[calc(100vh-20rem)] overflow-y-auto pr-2">
                                <AnimatePresence>
                                    {entities.length === 0 && (
                                        <motion.div
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                            exit={{ opacity: 0 }}
                                            className="text-center py-16 text-gray-500"
                                        >
                                            <p>El Kernel está vacío. Añade una entidad para empezar.</p>
                                        </motion.div>
                                    )}
                                    {entities.map(entity => <EntityCard key={entity.id} entity={entity} />)}
                                </AnimatePresence>
                            </div>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    );
};

export default KernelPanel;