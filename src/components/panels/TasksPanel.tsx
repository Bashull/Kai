import React, { useMemo, useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { AnimatePresence, motion } from 'framer-motion';
import { CheckSquare, Plus, Trash2, Calendar, Play, Bot } from 'lucide-react';
import Button from '../ui/Button';
import Checkbox from '../ui/Checkbox';
import { Task } from '../../types';
import { format, isToday, isPast } from 'date-fns';
import { es } from 'date-fns/locale';
import { getTaskPriority } from '../../utils/taskPriority';

const PRIORITY_CONFIG: Record<Task['priority'], { label: string; badgeClass: string; dotClass: string }> = {
    HIGH: {
        label: 'Alta',
        badgeClass: 'border-red-500/40 text-red-300 bg-red-500/10',
        dotClass: 'bg-red-400',
    },
    MEDIUM: {
        label: 'Media',
        badgeClass: 'border-amber-500/40 text-amber-200 bg-amber-500/10',
        dotClass: 'bg-amber-300',
    },
    LOW: {
        label: 'Baja',
        badgeClass: 'border-emerald-500/40 text-emerald-200 bg-emerald-500/10',
        dotClass: 'bg-emerald-300',
    },
};

type PriorityFilter = 'ALL' | Task['priority'];

const PriorityBadge: React.FC<{ priority?: Task['priority'] }> = ({ priority }) => {
    const resolvedPriority = getTaskPriority(priority);
    const config = PRIORITY_CONFIG[resolvedPriority];
    return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold rounded-full border ${config.badgeClass}`}>
            <span className={`w-2 h-2 rounded-full ${config.dotClass}`} aria-hidden />
            Prioridad {config.label}
        </span>
    );
};

const PrioritySelector: React.FC<{
    value?: Task['priority'];
    onChange: (priority: Task['priority']) => void;
    disabled?: boolean;
}> = ({ value, onChange, disabled }) => {
    const resolvedValue = getTaskPriority(value);
    return (
        <select
            value={resolvedValue}
            onChange={(event) => onChange(event.target.value as Task['priority'])}
            disabled={disabled}
            className="bg-transparent border border-border-color rounded-md px-2 py-1 text-xs text-text-secondary focus:outline-none focus:ring-2 focus:ring-kai-primary/60 disabled:opacity-60"
            aria-label="Cambiar prioridad"
        >
            {Object.entries(PRIORITY_CONFIG).map(([priorityKey, config]) => (
                <option key={priorityKey} value={priorityKey} className="bg-kai-surface text-text-primary">
                    {config.label}
                </option>
            ))}
        </select>
    );
};

const DueDateDisplay: React.FC<{ dueDate: string }> = ({ dueDate }) => {
    const date = new Date(dueDate);
    let displayText = `Vence ${format(date, 'd MMM', { locale: es })}`;
    if (isToday(date)) displayText = 'Vence Hoy';
    
    const isOverdue = isPast(date) && !isToday(date);
    
    return (
        <span className={`text-xs font-semibold ${isOverdue ? 'text-red-400' : 'text-text-secondary'}`}>
            {displayText}
        </span>
    );
};

const AgentLogViewer: React.FC<{ logs: Task['agentLogs'] }> = ({ logs }) => {
    if (!logs || logs.length === 0) return null;
    return (
        <div className="bg-black/40 rounded-lg p-3 mt-4 font-mono text-xs max-h-40 overflow-y-auto">
            {logs.map(log => (
                <div key={log.timestamp} className="flex items-start gap-2">
                    <span className="text-gray-500 shrink-0">{format(new Date(log.timestamp), 'HH:mm:ss')}</span>
                    <span className="text-gray-300 whitespace-pre-wrap">{log.message}</span>
                </div>
            ))}
        </div>
    );
};


const TaskItem: React.FC<{ task: Task }> = ({ task }) => {
    const { toggleTask, setTaskDueDate, isAutonomousMode, startAutonomousTask, setTaskPriority } = useAppStore();
    const isCompleted = task.status === 'COMPLETED';
    const isAgentRunning = task.agentStatus === 'RUNNING';
    const taskPriority = getTaskPriority(task.priority);

    const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setTaskDueDate(task.id, e.target.value || undefined);
    };

    const taskItemVariants = {
        initial: { opacity: 0, y: 20 },
        animate: { opacity: 1, y: 0 },
        exit: { opacity: 0, x: -20 },
    };

    return (
        <motion.li
            layout
            variants={taskItemVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="flex flex-col gap-4 p-4 bg-kai-surface/50 border border-border-color rounded-lg transition-colors duration-200 hover:bg-kai-surface"
        >
            <div className="flex items-start gap-4">
                <Checkbox
                    id={task.id}
                    checked={isCompleted}
                    onChange={() => toggleTask(task.id)}
                    disabled={isAgentRunning}
                />
                <div className="flex-grow space-y-2">
                     <div className="flex flex-wrap items-center gap-2">
                        <label
                            htmlFor={task.id}
                            className={`cursor-pointer transition-colors ${isCompleted ? 'text-text-secondary' : 'text-text-primary'} ${isAgentRunning ? 'cursor-not-allowed' : ''}`}
                        >
                             <span className={`${isCompleted ? 'line-through' : ''}`}>{task.title}</span>
                        </label>
                        <PriorityBadge priority={taskPriority} />
                        <PrioritySelector
                            value={taskPriority}
                            onChange={(priority) => setTaskPriority(task.id, priority)}
                            disabled={isAgentRunning}
                        />
                    </div>
                    {task.dueDate && !isCompleted && <div className="mt-1"><DueDateDisplay dueDate={task.dueDate} /></div> }
                </div>
                
                {!isCompleted && isAutonomousMode && (
                    <Button 
                        size="sm" 
                        variant="ghost" 
                        className="!p-2 text-kai-primary" 
                        onClick={() => startAutonomousTask(task.id)}
                        loading={isAgentRunning}
                        disabled={isAgentRunning}
                        title="Ejecutar Misión Autónomamente"
                    >
                        <Play size={16}/>
                    </Button>
                )}

                {!isAutonomousMode && !isCompleted && (
                    <div className="relative group">
                        <Calendar size={18} className="text-text-secondary cursor-pointer hover:text-text-primary" />
                        <input
                            type="date"
                            value={task.dueDate || ''}
                            onChange={handleDateChange}
                            className="absolute top-1/2 right-1/2 w-8 h-8 opacity-0 cursor-pointer"
                            aria-label="Fecha de vencimiento"
                        />
                    </div>
                )}
            </div>
             {task.agentLogs && task.agentLogs.length > 0 && <AgentLogViewer logs={task.agentLogs}/>}
        </motion.li>
    );
};

const TasksPanel: React.FC = () => {
    const { tasks, addTask, clearCompletedTasks, isAutonomousMode, toggleAutonomousMode } = useAppStore();
    const [newTaskTitle, setNewTaskTitle] = useState('');
    const [newTaskPriority, setNewTaskPriority] = useState<Task['priority']>('MEDIUM');
    const [priorityFilter, setPriorityFilter] = useState<PriorityFilter>('ALL');

    const pendingTasks = useMemo(
        () => tasks.filter(t => t.status === 'PENDING'),
        [tasks]
    );
    const completedTasks = useMemo(
        () => tasks.filter(t => t.status === 'COMPLETED'),
        [tasks]
    );

    const filterByPriority = (taskList: Task[]) =>
        priorityFilter === 'ALL'
            ? taskList
            : taskList.filter(task => getTaskPriority(task.priority) === priorityFilter);

    const filteredPendingTasks = useMemo(
        () => filterByPriority(pendingTasks),
        [pendingTasks, priorityFilter]
    );

    const filteredCompletedTasks = useMemo(
        () => filterByPriority(completedTasks),
        [completedTasks, priorityFilter]
    );

    const handleAddTask = (e: React.FormEvent) => {
        e.preventDefault();
        if (newTaskTitle.trim()) {
            addTask(newTaskTitle.trim(), newTaskPriority);
            setNewTaskTitle('');
            setNewTaskPriority('MEDIUM');
        }
    };

    return (
        <div>
            <h1 className="h1-title">Misiones</h1>
            <p className="p-subtitle">Mis objetivos y tareas actuales. Ayúdame a completarlos, o activa el Modo Autónomo y lo intentaré yo mismo.</p>

            <div className="max-w-3xl mx-auto mt-6 space-y-8">
                <div>
                     <div className="flex justify-between items-center mb-4">
                        <form onSubmit={handleAddTask} className="flex gap-2 flex-grow flex-wrap">
                            <input
                                type="text"
                                value={newTaskTitle}
                                onChange={(e) => setNewTaskTitle(e.target.value)}
                                placeholder="Añadir nueva misión..."
                                className="form-input flex-grow"
                            />
                            <select
                                value={newTaskPriority}
                                onChange={(event) => setNewTaskPriority(event.target.value as Task['priority'])}
                                className="bg-kai-surface border border-border-color rounded-md px-3 py-2 text-sm text-text-secondary focus:outline-none focus:ring-2 focus:ring-kai-primary/60"
                                aria-label="Prioridad de la nueva misión"
                            >
                                {Object.entries(PRIORITY_CONFIG).map(([priorityKey, config]) => (
                                    <option key={priorityKey} value={priorityKey} className="bg-kai-surface text-text-primary">
                                        Prioridad {config.label}
                                    </option>
                                ))}
                            </select>
                            <Button type="submit" icon={Plus} disabled={!newTaskTitle.trim()}>
                                Añadir
                            </Button>
                        </form>
                        <div className="flex items-center gap-2 ml-4 flex-shrink-0">
                            <label htmlFor="autonomous-mode" className={`text-sm font-medium transition-colors ${isAutonomousMode ? 'text-kai-primary' : 'text-text-secondary'}`}>
                                Modo Autónomo
                            </label>
                            <button
                                id="autonomous-mode"
                                onClick={toggleAutonomousMode}
                                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${isAutonomousMode ? 'bg-kai-primary' : 'bg-gray-600'}`}
                            >
                                <motion.span
                                    layout
                                    transition={{ type: 'spring', stiffness: 700, damping: 30 }}
                                    className="inline-block h-4 w-4 transform rounded-full bg-white"
                                    style={{x: isAutonomousMode ? '1.5rem' : '0.25rem' }}
                                />
                                <Bot size={12} className={`absolute text-gray-800 ${isAutonomousMode ? 'left-1.5' : 'right-1.5'}`}/>
                            </button>
                        </div>
                    </div>
                    <div className="flex flex-wrap gap-2 mb-4">
                        {([
                            { value: 'ALL', label: 'Todas' },
                            { value: 'HIGH', label: 'Alta' },
                            { value: 'MEDIUM', label: 'Media' },
                            { value: 'LOW', label: 'Baja' },
                        ] as { value: PriorityFilter; label: string }[]).map(filter => (
                            <button
                                key={filter.value}
                                onClick={() => setPriorityFilter(filter.value)}
                                className={`px-3 py-1 rounded-full text-sm border transition-colors ${priorityFilter === filter.value ? 'bg-kai-primary text-white border-kai-primary' : 'border-border-color text-text-secondary hover:text-text-primary hover:border-kai-primary/50'}`}
                                type="button"
                            >
                                {filter.label}
                            </button>
                        ))}
                    </div>
                    <AnimatePresence>
                        <ul className="space-y-3">
                            {filteredPendingTasks.map(task => <TaskItem key={task.id} task={task} />)}
                        </ul>
                    </AnimatePresence>
                    {filteredPendingTasks.length === 0 && pendingTasks.length > 0 && (
                        <div className="text-center py-8 text-gray-500">
                             <CheckSquare className="mx-auto w-12 h-12 mb-2 text-green-500" />
                            <p className="font-semibold">No hay misiones con este filtro de prioridad.</p>
                        </div>
                    )}
                    {pendingTasks.length === 0 && tasks.length > 0 && (
                        <div className="text-center py-8 text-gray-500">
                             <CheckSquare className="mx-auto w-12 h-12 mb-2 text-green-500" />
                            <p className="font-semibold">¡Todas las misiones pendientes han sido completadas!</p>
                        </div>
                    )}
                     {tasks.length === 0 && (
                        <div className="text-center py-8 text-gray-500">
                            <p>No hay misiones. Añade una para empezar.</p>
                        </div>
                    )}
                </div>

                {completedTasks.length > 0 && (
                    <div>
                        <div className="flex justify-between items-center mb-4">
                            <h2 className="text-lg font-semibold text-text-secondary">Completadas ({completedTasks.length})</h2>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={clearCompletedTasks}
                                icon={Trash2}
                            >
                                Limpiar
                            </Button>
                        </div>
                        <AnimatePresence>
                             <ul className="space-y-3">
                                {filteredCompletedTasks.map(task => <TaskItem key={task.id} task={task} />)}
                            </ul>
                        </AnimatePresence>
                        {filteredCompletedTasks.length === 0 && completedTasks.length > 0 && (
                            <div className="text-center py-6 text-gray-500 text-sm">
                                <p>No hay misiones completadas con la prioridad seleccionada.</p>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default TasksPanel;
