import React, { useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { motion, AnimatePresence } from 'framer-motion';
import { Memory, MemoryType } from '../../types';
import { formatRelativeTime } from '../../utils/helpers';
import { 
  Brain, 
  MessageSquare, 
  BookOpen, 
  Star, 
  Calendar, 
  Tag, 
  Trash2, 
  Plus,
  Search,
  Filter
} from 'lucide-react';
import Button from '../ui/Button';

const iconMap: { [key in MemoryType]: React.ReactElement } = {
  CONVERSATION: <MessageSquare className="text-blue-400" />,
  KNOWLEDGE: <BookOpen className="text-green-400" />,
  PREFERENCE: <Star className="text-yellow-400" />,
  EVENT: <Calendar className="text-purple-400" />,
};

const typeLabels: { [key in MemoryType]: string } = {
  CONVERSATION: 'Conversación',
  KNOWLEDGE: 'Conocimiento',
  PREFERENCE: 'Preferencia',
  EVENT: 'Evento',
};

const MemoryCard: React.FC<{ memory: Memory }> = ({ memory }) => {
  const { deleteMemory, updateMemory } = useAppStore();

  const handleDelete = () => {
    if (window.confirm('¿Estás seguro de que quieres eliminar este recuerdo?')) {
      deleteMemory(memory.id);
    }
  };

  const cardVariants = {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, scale: 0.9, transition: { duration: 0.2 } },
  };

  return (
    <motion.div
      layout
      variants={cardVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={{ type: 'spring', stiffness: 400, damping: 40 }}
      className="panel-container hover:border-kai-primary/30 transition-colors"
    >
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0 w-10 h-10 bg-kai-surface border-2 border-border-color rounded-full flex items-center justify-center">
          {iconMap[memory.type]}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs px-2 py-1 rounded-full bg-kai-surface border border-border-color text-text-secondary">
                  {typeLabels[memory.type]}
                </span>
                {memory.importance >= 0.7 && (
                  <span className="text-xs px-2 py-1 rounded-full bg-yellow-500/10 border border-yellow-500/30 text-yellow-400">
                    Alta importancia
                  </span>
                )}
              </div>
              <p className="text-text-primary">{memory.content}</p>
              {memory.tags && memory.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-3">
                  {memory.tags.map((tag, idx) => (
                    <span
                      key={idx}
                      className="text-xs px-2 py-0.5 rounded bg-kai-primary/10 text-kai-primary flex items-center gap-1"
                    >
                      <Tag size={10} />
                      {tag}
                    </span>
                  ))}
                </div>
              )}
              <p className="text-xs text-text-secondary mt-3">
                {formatRelativeTime(memory.timestamp)} · Importancia: {memory.importance.toFixed(1)}
              </p>
            </div>
            <Button
              onClick={handleDelete}
              icon={Trash2}
              size="sm"
              variant="ghost"
              className="text-red-500 hover:bg-red-500/10 flex-shrink-0"
            />
          </div>
        </div>
      </div>
    </motion.div>
  );
};

const MemoryPanel: React.FC = () => {
  const { memories, addMemory } = useAppStore();
  const [filterType, setFilterType] = useState<MemoryType | 'ALL'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  
  // Add form state
  const [newContent, setNewContent] = useState('');
  const [newType, setNewType] = useState<MemoryType>('KNOWLEDGE');
  const [newImportance, setNewImportance] = useState(0.5);
  const [newTags, setNewTags] = useState('');

  const handleAddMemory = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContent.trim()) return;

    addMemory({
      content: newContent.trim(),
      type: newType,
      importance: newImportance,
      tags: newTags.split(',').map(t => t.trim()).filter(t => t.length > 0),
    });

    // Reset form
    setNewContent('');
    setNewType('KNOWLEDGE');
    setNewImportance(0.5);
    setNewTags('');
    setShowAddForm(false);
  };

  // Filter memories
  let filteredMemories = memories;
  
  if (filterType !== 'ALL') {
    filteredMemories = filteredMemories.filter(m => m.type === filterType);
  }
  
  if (searchQuery.trim()) {
    const query = searchQuery.toLowerCase();
    filteredMemories = filteredMemories.filter(
      m => m.content.toLowerCase().includes(query) ||
           m.tags?.some(tag => tag.toLowerCase().includes(query))
    );
  }

  const stats = {
    total: memories.length,
    conversations: memories.filter(m => m.type === 'CONVERSATION').length,
    knowledge: memories.filter(m => m.type === 'KNOWLEDGE').length,
    preferences: memories.filter(m => m.type === 'PREFERENCE').length,
    events: memories.filter(m => m.type === 'EVENT').length,
  };

  const emptyStateVariants = {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
  };

  return (
    <div>
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="h1-title">Memoria a Largo Plazo</h1>
          <p className="p-subtitle">
            Sistema de memoria persistente que almacena conocimientos, preferencias y experiencias importantes.
          </p>
        </div>
        <Button
          onClick={() => setShowAddForm(!showAddForm)}
          icon={Plus}
          variant="primary"
          size="sm"
        >
          Nuevo Recuerdo
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <div className="panel-container text-center">
          <div className="text-2xl font-bold text-kai-primary">{stats.total}</div>
          <div className="text-xs text-text-secondary mt-1">Total</div>
        </div>
        <div className="panel-container text-center">
          <div className="text-2xl font-bold text-blue-400">{stats.conversations}</div>
          <div className="text-xs text-text-secondary mt-1">Conversaciones</div>
        </div>
        <div className="panel-container text-center">
          <div className="text-2xl font-bold text-green-400">{stats.knowledge}</div>
          <div className="text-xs text-text-secondary mt-1">Conocimientos</div>
        </div>
        <div className="panel-container text-center">
          <div className="text-2xl font-bold text-yellow-400">{stats.preferences}</div>
          <div className="text-xs text-text-secondary mt-1">Preferencias</div>
        </div>
        <div className="panel-container text-center">
          <div className="text-2xl font-bold text-purple-400">{stats.events}</div>
          <div className="text-xs text-text-secondary mt-1">Eventos</div>
        </div>
      </div>

      {/* Add Memory Form */}
      <AnimatePresence>
        {showAddForm && (
          <motion.form
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            onSubmit={handleAddMemory}
            className="panel-container mb-6"
          >
            <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
              <Plus size={20} className="text-kai-primary" />
              Añadir Nuevo Recuerdo
            </h3>
            <div className="space-y-4">
              <div>
                <label className="form-label">Contenido del recuerdo</label>
                <textarea
                  value={newContent}
                  onChange={(e) => setNewContent(e.target.value)}
                  className="form-input min-h-[100px]"
                  placeholder="Describe el recuerdo que quieres guardar..."
                  required
                />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="form-label">Tipo</label>
                  <select
                    value={newType}
                    onChange={(e) => setNewType(e.target.value as MemoryType)}
                    className="form-input"
                  >
                    <option value="KNOWLEDGE">Conocimiento</option>
                    <option value="CONVERSATION">Conversación</option>
                    <option value="PREFERENCE">Preferencia</option>
                    <option value="EVENT">Evento</option>
                  </select>
                </div>
                <div>
                  <label className="form-label">
                    Importancia: {newImportance.toFixed(1)}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={newImportance}
                    onChange={(e) => setNewImportance(parseFloat(e.target.value))}
                    className="w-full"
                  />
                </div>
              </div>
              <div>
                <label className="form-label">
                  Etiquetas (separadas por comas)
                </label>
                <input
                  type="text"
                  value={newTags}
                  onChange={(e) => setNewTags(e.target.value)}
                  className="form-input"
                  placeholder="programación, python, tutorial"
                />
              </div>
              <div className="flex gap-2">
                <Button type="submit" variant="primary">
                  Guardar Recuerdo
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setShowAddForm(false)}
                >
                  Cancelar
                </Button>
              </div>
            </div>
          </motion.form>
        )}
      </AnimatePresence>

      {/* Filters and Search */}
      <div className="panel-container mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-text-secondary" size={18} />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="form-input pl-10"
                placeholder="Buscar en recuerdos..."
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Filter size={18} className="text-text-secondary" />
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value as MemoryType | 'ALL')}
              className="form-input"
            >
              <option value="ALL">Todos los tipos</option>
              <option value="CONVERSATION">Conversaciones</option>
              <option value="KNOWLEDGE">Conocimientos</option>
              <option value="PREFERENCE">Preferencias</option>
              <option value="EVENT">Eventos</option>
            </select>
          </div>
        </div>
      </div>

      {/* Memory List */}
      <div className="space-y-4">
        <AnimatePresence mode="popLayout">
          {filteredMemories.length === 0 ? (
            <motion.div
              variants={emptyStateVariants}
              initial="initial"
              animate="animate"
              className="text-center py-16 text-gray-500"
            >
              <Brain size={48} className="mx-auto mb-4 opacity-50" />
              {memories.length === 0 ? (
                <>
                  <p className="text-lg font-semibold mb-2">No hay recuerdos aún</p>
                  <p className="text-sm">
                    Los recuerdos se crean automáticamente al resumir conversaciones, o puedes añadirlos manualmente.
                  </p>
                </>
              ) : (
                <>
                  <p className="text-lg font-semibold mb-2">No se encontraron recuerdos</p>
                  <p className="text-sm">Intenta ajustar los filtros o la búsqueda.</p>
                </>
              )}
            </motion.div>
          ) : (
            filteredMemories.map((memory) => (
              <MemoryCard key={memory.id} memory={memory} />
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default MemoryPanel;
