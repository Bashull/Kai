import React from "react";
import { Loader2, CheckCircle, Circle } from "lucide-react";

interface MissionStatusBadgeProps {
  status: "PENDING" | "COMPLETED";
  agentStatus?: "IDLE" | "RUNNING" | "COMPLETED";
}

const MissionStatusBadge: React.FC<MissionStatusBadgeProps> = ({ status, agentStatus }) => {
  if (agentStatus === "RUNNING") {
    return (
      <div className="inline-flex items-center gap-2 text-xs font-semibold px-2.5 py-1 rounded-full bg-purple-600/20 text-purple-300">
        <Loader2 size={14} className="animate-spin" />
        <span>Agente Activo</span>
      </div>
    );
  }

  if (status === "COMPLETED") {
    return (
      <div className="inline-flex items-center gap-2 text-xs font-semibold px-2.5 py-1 rounded-full bg-green-600/20 text-green-300">
        <CheckCircle size={14} />
        <span>Completada</span>
      </div>
    );
  }

  return (
    <div className="inline-flex items-center gap-2 text-xs font-semibold px-2.5 py-1 rounded-full bg-gray-600/20 text-gray-300">
      <Circle size={14} />
      <span>Pendiente</span>
    </div>
  );
};

export default MissionStatusBadge;
