import { NotificationSlice, AppSlice } from '../../types';
import { generateId } from '../../utils/helpers';

export const createNotificationSlice: AppSlice<NotificationSlice> = (set, get) => ({
  notifications: [],
  addNotification: (notification) => {
    const id = generateId();
    set((state) => ({
      notifications: [...state.notifications, { ...notification, id }],
    }));
    setTimeout(() => {
      get().removeNotification(id);
    }, 5000); // Auto-dismiss after 5 seconds
  },
  removeNotification: (id) => {
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    }));
  },
});
