import React from 'react';
import { Loader2, CheckCircle, XCircle, Hourglass } from 'lucide-react';
// FIX: Replaced aliased import path with a relative path.
import { TrainingJobStatus } from '../../types';

interface TrainingJobStatusBadgeProps {
  status: TrainingJobStatus;
}

const statusConfig = {
  QUEUED: {
    label: 'En Cola',
    icon: Hourglass,
    className: 'bg-yellow-600/20 text-yellow-300',
  },
  TRAINING: {
    label: 'Entrenando',
    icon: Loader2,
    className: 'bg-blue-600/20 text-blue-300',
  },
  COMPLETED: {
    label: 'Completado',
    icon: CheckCircle,
    className: 'bg-green-600/20 text-green-300',
  },
  FAILED: {
    label: 'Fallido',
    icon: XCircle,
    className: 'bg-red-600/20 text-red-300',
  },
};

const TrainingJobStatusBadge: React.FC<TrainingJobStatusBadgeProps> = ({ status }) => {
  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <div className={`flex-shrink-0 inline-flex items-center gap-2 text-xs font-semibold px-2.5 py-1 rounded-full ${config.className}`}>
      <Icon size={14} className={status === 'TRAINING' ? 'animate-spin' : ''} />
      <span>{config.label}</span>
    </div>
  );
};

export default TrainingJobStatusBadge;