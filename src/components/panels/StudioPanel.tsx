import React, { useEffect, useRef } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { checkAIAccess } from '../../services/geminiService';
import Button from '../ui/Button';
import { Terminal, Check, X, ShieldQuestion, Trash2 } from 'lucide-react';
import { format } from 'date-fns';
import { StudioLog } from '../../types';

const LogLine: React.FC<{ log: StudioLog }> = ({ log }) => {
    const typeStyles = {
        COMMAND: 'text-kai-primary',
        RESPONSE: 'text-green-400',
        ERROR: 'text-red-400',
        INFO: 'text-gray-400',
    };
    const prefix = {
        COMMAND: '> ',
        RESPONSE: '< ',
        ERROR: '! ',
        INFO: '# ',
    }
    return (
        <div className="flex items-start gap-3">
            <span className="text-gray-600 shrink-0">{format(new Date(log.timestamp), 'HH:mm:ss')}</span>
            <pre className={`whitespace-pre-wrap break-all ${typeStyles[log.type]}`}>
                <code>{prefix[log.type]}{log.content}</code>
            </pre>
        </div>
    );
}

const StudioPanel: React.FC = () => {
    const { isChecking, studioLogs, setIsChecking, addStudioLog, clearStudioLogs } = useAppStore();
    const logContainerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if(logContainerRef.current) {
            logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
        }
    }, [studioLogs]);

    const handleCheckAccess = async () => {
        if (isChecking) return;

        setIsChecking(true);
        addStudioLog({ type: 'COMMAND', content: 'checkAIAccess()' });

        const result = await checkAIAccess();

        if (result.trim() === 'PONG') {
            addStudioLog({ type: 'RESPONSE', content: `Prueba de acceso superada. Respuesta del núcleo: ${result}` });
        } else if (result.startsWith('ERROR:')) {
            addStudioLog({ type: 'ERROR', content: `Prueba de acceso fallida. ${result}`});
        } else {
             addStudioLog({ type: 'ERROR', content: `Respuesta inesperada del núcleo: ${result}` });
        }
        setIsChecking(false);
    };

    return (
        <div>
            <h1 className="h1-title">IA Studio</h1>
            <p className="p-subtitle">Mi consola de operaciones para diagnóstico y monitorización del sistema.</p>

            <div className="panel-container">
                 <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-4">
                    <div className="flex items-center gap-3">
                        <Terminal className="w-6 h-6 text-kai-primary" />
                        <h2 className="text-xl font-bold">Consola del Sistema</h2>
                    </div>
                    <div className="flex gap-2">
                        <Button onClick={handleCheckAccess} loading={isChecking} icon={ShieldQuestion}>
                            Verificar Acceso al Núcleo de IA
                        </Button>
                         <Button onClick={clearStudioLogs} variant="secondary" icon={Trash2} title="Clear Logs"/>
                    </div>
                </div>

                <div ref={logContainerRef} className="bg-black/50 font-mono text-sm p-4 rounded-lg h-96 overflow-y-auto border border-border-color">
                    {studioLogs.length === 0 ? (
                         <p className="text-gray-500"># El registro del sistema está vacío. Inicia una verificación.</p>
                    ) : (
                        studioLogs.map(log => <LogLine key={log.id} log={log} />)
                    )}
                </div>
            </div>
        </div>
    );
};

export default StudioPanel;
