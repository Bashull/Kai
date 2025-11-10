import React, { useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import Button from '../ui/Button';
import { Trash2, Plus, History, Shield } from 'lucide-react';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import Modal from '../ui/Modal';

const SettingsPanel: React.FC = () => {
    const { 
        theme, 
        setTheme, 
        sidebarCollapsed, 
        toggleSidebar,
        constitution,
        versionHistory,
        updateConstitution,
        revertToVersion
    } = useAppStore();

    const [isEditingConstitution, setIsEditingConstitution] = useState(false);
    const [editedConstitution, setEditedConstitution] = useState(constitution);
    const [showHistory, setShowHistory] = useState(false);
    const [newPrinciple, setNewPrinciple] = useState('');

    const handleSaveConstitution = () => {
        updateConstitution(editedConstitution);
        setIsEditingConstitution(false);
    };

    const handleCancelEdit = () => {
        setEditedConstitution(constitution);
        setIsEditingConstitution(false);
    };

    const handleAddPrinciple = () => {
        if (newPrinciple.trim()) {
            setEditedConstitution({
                ...editedConstitution,
                principles: [...editedConstitution.principles, newPrinciple.trim()],
            });
            setNewPrinciple('');
        }
    };

    const handleRemovePrinciple = (index: number) => {
        setEditedConstitution({
            ...editedConstitution,
            principles: editedConstitution.principles.filter((_, i) => i !== index),
        });
    };

    const handleRevertToVersion = (version: number) => {
        revertToVersion(version);
        setShowHistory(false);
        setIsEditingConstitution(false);
    };

    const handleClearLocalStorage = () => {
        if (window.confirm('¿Estás seguro de que deseas borrar todos los datos locales? Esta acción no se puede deshacer.')) {
            localStorage.clear();
            window.location.reload();
        }
    };

    return (
        <div>
            <h1 className="h1-title">Ajustes</h1>
            <p className="p-subtitle">Personaliza tu experiencia con KaiOS.</p>

            <div className="space-y-8 max-w-4xl mt-6">
                {/* Appearance Settings */}
                <div className="panel-container">
                    <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                        Apariencia
                    </h2>
                    <div className="space-y-4">
                        <div>
                            <label className="form-label">Tema Visual</label>
                            <div className="flex gap-2">
                                <Button onClick={() => setTheme('light')} variant={theme === 'light' ? 'primary' : 'secondary'}>Claro</Button>
                                <Button onClick={() => setTheme('dark')} variant={theme === 'dark' ? 'primary' : 'secondary'}>Oscuro</Button>
                            </div>
                        </div>
                        <div>
                            <label className="form-label">Barra Lateral</label>
                            <div className="flex items-center">
                                <input 
                                    type="checkbox" 
                                    id="collapse-sidebar"
                                    className="h-4 w-4 rounded border-gray-500 bg-gray-700 text-kai-primary focus:ring-kai-primary"
                                    checked={sidebarCollapsed}
                                    onChange={toggleSidebar}
                                />
                                <label htmlFor="collapse-sidebar" className="ml-2 text-sm text-gray-300">Contraer Barra Lateral</label>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Constitution Management */}
                <div className="panel-container">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold flex items-center gap-2">
                            <Shield className="w-5 h-5 text-kai-primary" />
                            Constitución de Kai
                        </h2>
                        <div className="flex gap-2">
                            <Button 
                                size="sm" 
                                variant="secondary" 
                                icon={History}
                                onClick={() => setShowHistory(true)}
                            >
                                Historial (v{versionHistory[0]?.version})
                            </Button>
                            {!isEditingConstitution && (
                                <Button 
                                    size="sm" 
                                    onClick={() => {
                                        setEditedConstitution(constitution);
                                        setIsEditingConstitution(true);
                                    }}
                                >
                                    Editar
                                </Button>
                            )}
                        </div>
                    </div>

                    {!isEditingConstitution ? (
                        <>
                            <div className="mb-4">
                                <h3 className="text-sm font-semibold text-kai-primary mb-2">Directiva Maestra</h3>
                                <p className="text-sm text-text-secondary">{constitution.masterDirective}</p>
                            </div>
                            <div>
                                <h3 className="text-sm font-semibold text-kai-primary mb-2">Principios</h3>
                                <ul className="space-y-2">
                                    {constitution.principles.map((principle, index) => (
                                        <li key={index} className="text-sm text-text-secondary flex items-start gap-2">
                                            <span className="text-kai-primary font-mono">{index + 1}.</span>
                                            <span>{principle}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </>
                    ) : (
                        <>
                            <div className="mb-4">
                                <label className="form-label">Directiva Maestra</label>
                                <textarea
                                    className="form-input min-h-[100px]"
                                    value={editedConstitution.masterDirective}
                                    onChange={(e) => setEditedConstitution({
                                        ...editedConstitution,
                                        masterDirective: e.target.value
                                    })}
                                />
                            </div>
                            <div>
                                <label className="form-label">Principios</label>
                                <div className="space-y-2 mb-3">
                                    {editedConstitution.principles.map((principle, index) => (
                                        <div key={index} className="flex items-start gap-2">
                                            <span className="text-kai-primary font-mono text-sm mt-3">{index + 1}.</span>
                                            <textarea
                                                className="form-input flex-1 min-h-[60px]"
                                                value={principle}
                                                onChange={(e) => {
                                                    const newPrinciples = [...editedConstitution.principles];
                                                    newPrinciples[index] = e.target.value;
                                                    setEditedConstitution({
                                                        ...editedConstitution,
                                                        principles: newPrinciples
                                                    });
                                                }}
                                            />
                                            <Button
                                                size="sm"
                                                variant="secondary"
                                                icon={Trash2}
                                                onClick={() => handleRemovePrinciple(index)}
                                                className="mt-2"
                                            />
                                        </div>
                                    ))}
                                </div>
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        className="form-input flex-1"
                                        placeholder="Agregar nuevo principio..."
                                        value={newPrinciple}
                                        onChange={(e) => setNewPrinciple(e.target.value)}
                                        onKeyDown={(e) => e.key === 'Enter' && handleAddPrinciple()}
                                    />
                                    <Button size="sm" icon={Plus} onClick={handleAddPrinciple}>
                                        Agregar
                                    </Button>
                                </div>
                            </div>
                            <div className="flex gap-2 mt-6">
                                <Button variant="primary" onClick={handleSaveConstitution}>
                                    Guardar Cambios
                                </Button>
                                <Button variant="secondary" onClick={handleCancelEdit}>
                                    Cancelar
                                </Button>
                            </div>
                        </>
                    )}
                </div>

                {/* Data Management */}
                <div className="panel-container">
                    <h2 className="text-lg font-semibold mb-3">Gestión de Datos</h2>
                    <div className="space-y-3">
                        <p className="text-sm text-text-secondary">
                            Los datos de KaiOS se almacenan localmente en tu navegador. Puedes borrarlos en cualquier momento.
                        </p>
                        <Button 
                            variant="secondary" 
                            onClick={handleClearLocalStorage}
                            icon={Trash2}
                        >
                            Borrar Datos Locales
                        </Button>
                    </div>
                </div>

                {/* About */}
                <div className="panel-container">
                    <h2 className="text-lg font-semibold mb-3">Acerca de</h2>
                    <p className="text-sm text-text-secondary">
                        Estás interactuando con KaiOS, un compañero de IA relacional.
                        <br/>
                        Versión de la Shell: 3.0 (Génesis)
                        <br/>
                        Constitución: v{versionHistory[0]?.version} • Última actualización: {format(new Date(versionHistory[0]?.date), 'PPP', { locale: es })}
                    </p>
                </div>
            </div>

            {/* Constitution History Modal */}
            <Modal 
                isOpen={showHistory} 
                onClose={() => setShowHistory(false)}
                title="Historial de Constitución"
            >
                <div className="space-y-4 max-h-[60vh] overflow-y-auto">
                    {versionHistory.map((version) => (
                        <div key={version.version} className="border border-gray-700 rounded-lg p-4">
                            <div className="flex items-center justify-between mb-3">
                                <div>
                                    <span className="text-sm font-semibold text-kai-primary">
                                        Versión {version.version}
                                    </span>
                                    <span className="text-xs text-text-secondary ml-2">
                                        {format(new Date(version.date), 'PPpp', { locale: es })}
                                    </span>
                                </div>
                                {version.version !== versionHistory[0].version && (
                                    <Button 
                                        size="sm" 
                                        variant="secondary"
                                        onClick={() => handleRevertToVersion(version.version)}
                                    >
                                        Restaurar
                                    </Button>
                                )}
                            </div>
                            <div className="text-xs text-text-secondary">
                                <p className="mb-2">{version.constitution.masterDirective}</p>
                                <div className="space-y-1">
                                    {version.constitution.principles.map((p, i) => (
                                        <div key={i}>• {p}</div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </Modal>
        </div>
    );
}

export default SettingsPanel;
