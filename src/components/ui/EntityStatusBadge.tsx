import React from 'react';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';
// FIX: Replaced aliased import path with a relative path.
import { EntityStatus } from '../../types';

interface EntityStatusBadgeProps {
  status: EntityStatus;
}

const statusConfig = {
  ASSIMILATING: {
    label: 'Asimilando',
    icon: Loader2,
    className: 'bg-blue-600/20 text-blue-300',
  },
  INTEGRATED: {
    label: 'Integrada',
    icon: CheckCircle,
    className: 'bg-green-600/20 text-green-300',
  },
  REJECTED: {
    label: 'Rechazada',
    icon: XCircle,
    className: 'bg-red-600/20 text-red-300',
  },
};

const EntityStatusBadge: React.FC<EntityStatusBadgeProps> = ({ status }) => {
  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <div className={`inline-flex items-center gap-2 text-xs font-semibold px-2.5 py-1 rounded-full ${config.className}`}>
      <Icon size={14} className={status === 'ASSIMILATING' ? 'animate-spin' : ''} />
      <span>{config.label}</span>
    </div>
  );
};

export default EntityStatusBadge;