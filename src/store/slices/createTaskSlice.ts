import { TaskSlice, AppSlice, Task } from '../../types';
import { generateId } from '../../utils/helpers';

const initialTasks: Task[] = [
    {
        id: 'task-1',
        title: 'Verificar la conexión con el núcleo de IA en la Consola del Sistema.',
        status: 'PENDING',
        createdAt: new Date().toISOString(),
        dueDate: new Date().toISOString().split('T')[0], // Due today
    },
    {
        id: 'task-2',
        title: 'Asimilar una nueva entidad de tipo URL en el Kernel.',
        status: 'PENDING',
        createdAt: new Date().toISOString(),
    },
    {
        id: 'task-3',
        title: 'Iniciar un nuevo trabajo de fine-tuning en La Forja.',
        status: 'PENDING',
        createdAt: new Date().toISOString(),
    },
     {
        id: 'task-4',
        title: 'Generar una imagen de "un gato programando en una laptop" en el IA Studio.',
        status: 'COMPLETED',
        createdAt: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
    },
];


export const createTaskSlice: AppSlice<TaskSlice> = (set) => ({
    tasks: initialTasks,
    addTask: (title: string) => set(state => ({
        tasks: [
            {
                id: generateId(),
                title,
                status: 'PENDING',
                createdAt: new Date().toISOString(),
            },
            ...state.tasks,
        ],
    })),
    toggleTask: (id: string) => set(state => ({
        tasks: state.tasks.map(task =>
            task.id === id ? { ...task, status: task.status === 'PENDING' ? 'COMPLETED' : 'PENDING' } : task
        ),
    })),
    clearCompletedTasks: () => set(state => ({
        tasks: state.tasks.filter(task => task.status !== 'COMPLETED'),
    })),
    setTaskDueDate: (id: string, dueDate: string | undefined) => set(state => ({
        tasks: state.tasks.map(task =>
            task.id === id ? { ...task, dueDate } : task
        ),
    })),
});