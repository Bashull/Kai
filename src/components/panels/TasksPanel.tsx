import React, { useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { AnimatePresence, motion } from 'framer-motion';
import { CheckSquare, Plus, Trash2, Calendar } from 'lucide-react';
import Button from '../ui/Button';
import Checkbox from '../ui/Checkbox';
import { Task } from '../../types';
import { format, isToday, isPast, parseISO } from 'date-fns';
import { es } from 'date-fns/locale';

const DueDateDisplay: React.FC<{ dueDate: string }> = ({ dueDate }) => {
    const date = parseISO(dueDate);
    let displayText = `Vence ${format(date, 'd MMM', { locale: es })}`;
    if (isToday(date)) displayText = 'Vence Hoy';
    
    const isOverdue = isPast(date) && !isToday(date);
    
    return (
        <span className={`text-xs font-semibold ${isOverdue ? 'text-red-400' : 'text-text-secondary'}`}>
            {displayText}
        </span>
    );
}

const TaskItem: React.FC<{ task: Task }> = ({ task }) => {
    const { toggleTask, setTaskDueDate } = useAppStore.getState();
    const isCompleted = task.status === 'COMPLETED';

    const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setTaskDueDate(task.id, e.target.value || undefined);
    };

    return (
        <motion.li
            layout
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="flex items-center gap-4 p-4 bg-kai-surface/50 border border-border-color rounded-lg transition-colors duration-200 hover:bg-kai-surface"
        >
            <Checkbox
                id={task.id}
                checked={isCompleted}
                onChange={() => toggleTask(task.id)}
            />
            <div className="flex-grow">
                 <label
                    htmlFor={task.id}
                    className={`cursor-pointer transition-colors ${isCompleted ? 'text-text-secondary' : 'text-text-primary'}`}
                >
                     <span className={`line-through ${isCompleted ? 'completed' : ''}`}>{task.title}</span>
                </label>
                {task.dueDate && !isCompleted && <div className="mt-1"><DueDateDisplay dueDate={task.dueDate} /></div> }
            </div>
            
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
           
        </motion.li>
    );
};

const TasksPanel: React.FC = () => {
    const { tasks, addTask, clearCompletedTasks } = useAppStore();
    const [newTaskTitle, setNewTaskTitle] = useState('');

    const pendingTasks = tasks.filter(t => t.status === 'PENDING');
    const completedTasks = tasks.filter(t => t.status === 'COMPLETED');

    const handleAddTask = (e: React.FormEvent) => {
        e.preventDefault();
        if (newTaskTitle.trim()) {
            addTask(newTaskTitle.trim());
            setNewTaskTitle('');
        }
    };

    return (
        <div>
            <h1 className="h1-title">Misiones</h1>
            <p className="p-subtitle">Mis objetivos y tareas actuales. Ayúdame a completarlos.</p>

            <div className="max-w-3xl mx-auto mt-6 space-y-8">
                <div>
                    <form onSubmit={handleAddTask} className="flex gap-2 mb-4">
                        <input
                            type="text"
                            value={newTaskTitle}
                            onChange={(e) => setNewTaskTitle(e.target.value)}
                            placeholder="Añadir nueva misión..."
                            className="form-input flex-grow"
                        />
                        <Button type="submit" icon={Plus} disabled={!newTaskTitle.trim()}>
                            Añadir
                        </Button>
                    </form>
                    <AnimatePresence>
                        <ul className="space-y-3">
                            {pendingTasks.map(task => <TaskItem key={task.id} task={task} />)}
                        </ul>
                    </AnimatePresence>
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
                                {completedTasks.map(task => <TaskItem key={task.id} task={task} />)}
                            </ul>
                        </AnimatePresence>
                    </div>
                )}
            </div>
        </div>
    );
};

export default TasksPanel;