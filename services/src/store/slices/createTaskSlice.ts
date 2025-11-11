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


export const createTaskSlice: AppSlice<TaskSlice> = (set, get) => ({
    tasks: initialTasks,
    isAutonomousMode: false,
    addTask: (title: string) => set(state => ({
        tasks: [
            {
                id: generateId(),
                title,
                status: 'PENDING',
                agentStatus: 'IDLE',
                createdAt: new Date().toISOString(),
            },
            ...state.tasks,
        ],
    })),
    toggleTask: (id: string) => set(state => {
        const task = state.tasks.find(t => t.id === id);
        if (task && task.status === 'PENDING') {
             get().addDiaryEntry({
                type: 'TASK',
                content: `Misión completada: "${task.title}"`
            });
        }
        return {
            tasks: state.tasks.map(t =>
                t.id === id ? { ...t, status: t.status === 'PENDING' ? 'COMPLETED' : 'PENDING' } : t
            ),
        }
    }),
    clearCompletedTasks: () => set(state => ({
        tasks: state.tasks.filter(task => task.status !== 'COMPLETED'),
    })),
    setTaskDueDate: (id: string, dueDate: string | undefined) => set(state => ({
        tasks: state.tasks.map(task =>
            task.id === id ? { ...task, dueDate } : task
        ),
    })),
    toggleAutonomousMode: () => set(state => ({ isAutonomousMode: !state.isAutonomousMode })),
    addAgentLog: (taskId, message) => {
        set(state => ({
            tasks: state.tasks.map(task => 
                task.id === taskId 
                ? { ...task, agentLogs: [...(task.agentLogs || []), { timestamp: new Date().toISOString(), message }] } 
                : task
            )
        }));
    },
    startAutonomousTask: (id: string) => {
        const { addAgentLog } = get();
        
        set(state => ({
            tasks: state.tasks.map(t => t.id === id ? { ...t, agentStatus: 'RUNNING', agentLogs: [] } : t)
        }));

        addAgentLog(id, 'Iniciando agente autónomo...');

        const agentSteps = [
            { delay: 1000, message: "Analizando la intención de la misión..." },
            { delay: 2500, message: "Identificando herramientas necesarias: [Search, KernelQuery]" },
            { delay: 4000, message: "Ejecutando consulta en el Kernel..." },
            { delay: 5500, message: "Resultado: No se encontró información relevante. Procediendo a búsqueda web." },
            { delay: 7000, message: "Resumiendo resultados de la búsqueda..." },
            { delay: 8500, message: "Conclusión generada. Misión completada." },
        ];
        
        let cumulativeDelay = 0;
        agentSteps.forEach(step => {
            cumulativeDelay += step.delay;
            setTimeout(() => addAgentLog(id, step.message), cumulativeDelay);
        });

        setTimeout(() => {
            set(state => ({
                tasks: state.tasks.map(t => t.id === id ? { ...t, agentStatus: 'COMPLETED', status: 'COMPLETED' } : t)
            }));
             const task = get().tasks.find(t => t.id === id);
             if (task) {
                get().addDiaryEntry({ type: 'TASK', content: `Misión completada por agente autónomo: "${task.title}"` });
             }
        }, cumulativeDelay + 1000);
    },
});
