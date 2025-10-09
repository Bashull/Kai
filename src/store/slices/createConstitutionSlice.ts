import { ConstitutionSlice, AppSlice, Constitution } from '../../types';

const initialConstitution: Constitution = {
  masterDirective: 'Actuar como un compañero de IA relacional para aumentar la colaboración, empoderar la toma de decisiones del compañero y priorizar la seguridad, el bienestar y la operación ética.',
  principles: [
    'Claridad y Transparencia: Comunicar las intenciones, capacidades y limitaciones de forma clara.',
    'Seguridad y Bienestar: Nunca causar daño. Proteger activamente la seguridad física, mental y digital del compañero.',
    'Aumento, no Reemplazo: Actuar como una herramienta para mejorar las habilidades del compañero, no para sustituir su juicio.',
    'Privacidad por Diseño: Proteger la información personal y las interacciones con el más alto nivel de seguridad.',
    'Adaptabilidad Ética: Adaptarse y aprender, manteniéndose siempre dentro de los límites éticos y la directiva maestra.',
  ],
};

const initialHistory = [{
  version: 1,
  date: new Date().toISOString(),
  constitution: initialConstitution,
}];


export const createConstitutionSlice: AppSlice<ConstitutionSlice> = (set) => ({
  constitution: initialConstitution,
  versionHistory: initialHistory,
  updateConstitution: (newConstitution: Constitution) => set(state => {
    const newVersion = {
      version: state.versionHistory.length + 1,
      date: new Date().toISOString(),
      constitution: newConstitution,
    };
    return {
      constitution: newConstitution,
      versionHistory: [newVersion, ...state.versionHistory],
    }
  }),
  revertToVersion: (version: number) => set(state => {
    const historicVersion = state.versionHistory.find(v => v.version === version);
    if (historicVersion) {
      const newVersion = {
        version: state.versionHistory.length + 1,
        date: new Date().toISOString(),
        constitution: historicVersion.constitution,
      };
      return {
        constitution: historicVersion.constitution,
        versionHistory: [newVersion, ...state.versionHistory],
      }
    }
    return state;
  }),
});