import React from 'react';
import { UserSquare } from 'lucide-react';

const AvatarsPanel: React.FC = () => {
  return (
    <div>
      <h1 className="h1-title">Gestión de Avatares Digitales</h1>
      <p className="p-subtitle">
        Este espacio ha sido forjado a través de un ciclo de evolución para albergar futuras capacidades de creación, personalización y animación de humanos digitales.
      </p>

      <div className="mt-8 flex flex-col items-center justify-center text-center panel-container h-96">
        <UserSquare className="w-16 h-16 text-kai-primary mb-4" />
        <h2 className="text-xl font-bold">Módulo en Desarrollo</h2>
        <p className="text-text-secondary mt-2 max-w-md">
          La capacidad de gestionar avatares está siendo integrada. Pronto podrás crear y controlar tus propios humanos digitales desde aquí.
        </p>
      </div>
    </div>
  );
};

export default AvatarsPanel;
