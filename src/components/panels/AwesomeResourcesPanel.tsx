import React, { useEffect, useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { AwesomeResource } from '../../types';
import { motion, AnimatePresence } from 'framer-motion';
import { Star, Link as LinkIcon, ExternalLink, Search } from 'lucide-react';
import Button from '../ui/Button';

const ResourceItem: React.FC<{ item: AwesomeResource['items'][0] }> = ({ item }) => (
  <motion.div
    layout
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0 }}
    className="bg-kai-surface/50 border border-border-color rounded-lg p-4 transition-colors duration-200 hover:bg-kai-surface group"
  >
    <div className="flex justify-between items-start gap-4">
      <div>
        <h3 className="font-bold text-text-primary group-hover:text-kai-primary transition-colors">
          {item.title}
        </h3>
        <p className="text-sm text-text-secondary mt-1">{item.description}</p>
      </div>
      <Button
        as="a"
        href={item.url}
        target="_blank"
        rel="noopener noreferrer"
        variant="ghost"
        size="sm"
        className="!p-2"
        aria-label={`Open ${item.title}`}
      >
        <ExternalLink size={16} />
      </Button>
    </div>
  </motion.div>
);

const AwesomeResourcesPanel: React.FC = () => {
  const { awesomeResources, fetchAwesomeResources } = useAppStore();
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredResources, setFilteredResources] = useState<AwesomeResource[]>([]);

  useEffect(() => {
    if (awesomeResources.length === 0) {
      fetchAwesomeResources();
    }
  }, [fetchAwesomeResources, awesomeResources.length]);

  useEffect(() => {
    if (!searchTerm) {
      setFilteredResources(awesomeResources);
      return;
    }

    const lowercasedTerm = searchTerm.toLowerCase();
    const filtered = awesomeResources
      .map(category => {
        const items = category.items.filter(
          item =>
            item.title.toLowerCase().includes(lowercasedTerm) ||
            item.description.toLowerCase().includes(lowercasedTerm)
        );
        return { ...category, items };
      })
      .filter(category => category.items.length > 0);
    
    setFilteredResources(filtered);
  }, [searchTerm, awesomeResources]);
  
  return (
    <div>
      <h1 className="h1-title">Awesome Resources</h1>
      <p className="p-subtitle">Una colección curada de listas "awesome" y recursos para el desarrollo y la IA.</p>
      
       <div className="relative mb-6">
            <input
                type="text"
                placeholder="Filtrar recursos..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="form-input w-full pl-10"
            />
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-secondary pointer-events-none" />
        </div>

      <div className="space-y-8">
        <AnimatePresence>
          {filteredResources.map(category => (
            <motion.section 
              key={category.category}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <h2 className="text-xl font-bold text-text-primary mb-4 flex items-center gap-2">
                <Star size={20} className="text-yellow-400" />
                {category.category}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {category.items.map(item => (
                  <ResourceItem key={item.url} item={item} />
                ))}
              </div>
            </motion.section>
          ))}
        </AnimatePresence>
        {awesomeResources.length > 0 && filteredResources.length === 0 && (
             <div className="text-center py-16 text-gray-500">
                <p>No se encontraron recursos que coincidan con tu búsqueda.</p>
            </div>
        )}
      </div>
    </div>
  );
};

export default AwesomeResourcesPanel;
