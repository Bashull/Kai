import React from 'react';
import { useAppStore } from '../../store/useAppStore';
import Button from '../ui/Button';

const SettingsPanel: React.FC = () => {
    const { theme, setTheme, sidebarCollapsed, toggleSidebar } = useAppStore();

    return (
        <div>
            <h1 className="h1-title">Ajustes</h1>
            <p className="p-subtitle">Personaliza tu experiencia con KaiOS.</p>

            <div className="space-y-8 max-w-md">
                <div className="panel-container">
                    <h2 className="text-lg font-semibold mb-3">Apariencia</h2>
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
                 <div className="panel-container">
                    <h2 className="text-lg font-semibold mb-3">Acerca de</h2>
                    <p className="text-sm text-text-secondary">
                        Estás interactuando con KaiOS, un compañero de IA relacional.
                        <br/>
                        Versión de la Shell: 3.0 (Génesis)
                    </p>
                 </div>
            </div>
        </div>
    );
}

export default SettingsPanel;