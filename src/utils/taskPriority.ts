import { Task } from '../types';

export const DEFAULT_TASK_PRIORITY: Task['priority'] = 'MEDIUM';

export const getTaskPriority = (priority?: Task['priority']): Task['priority'] =>
    priority ?? DEFAULT_TASK_PRIORITY;

type TaskWithOptionalPriority = Omit<Task, 'priority'> & { priority?: Task['priority'] };

export const normalizeTaskPriority = (task: TaskWithOptionalPriority): Task => ({
    ...task,
    priority: getTaskPriority(task.priority),
});
