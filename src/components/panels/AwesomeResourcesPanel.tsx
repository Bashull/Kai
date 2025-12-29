import React, { useEffect } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { motion } from 'framer-motion';
import { Link, Star } from 'lucide-react';
import { AwesomeResource } from '../../types';

const ResourceCard: React.FC<{ item: AwesomeResource['items'][0] }> = ({ item }) => (
    <a 
        href={item.url} 
        target="_blank" 
        rel="noopener noreferrer"
        className="block p-4 bg-kai-surface/50 border border-border-color rounded-lg transition-colors duration-200 hover:bg-kai-surface hover:border-kai-primary"
    >
        <h4 className="font-semibold text-text-primary flex items-center gap-2">
            <Link size={14} />
            {item.title}
        </h4>
        <p className="text-sm text-text-secondary mt-1">{item.description}</p>
    </a>
);

const AwesomeResourcesPanel: React.FC = () => {
    const { awesomeResources, fetchAwesomeResources } = useAppStore();

    useEffect(() => {
        if (awesomeResources.length === 0) {
            fetchAwesomeResources();
        }
    }, [fetchAwesomeResources, awesomeResources.length]);

    const containerVariants = {
        hidden: { opacity: 0 },
        show: {
            opacity: 1,
            transition: {
                staggerChildren: 0.1,
            },
        },
    };

    const itemVariants = {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0 },
    };

    return (
        <div>
            <h1 className="h1-title">Recursos Awesome</h1>
            <p className="p-subtitle">Una lista curada de recursos y herramientas que forman parte de mi base de conocimiento y capacidades evolutivas.</p>

            <motion.div 
                className="mt-6 space-y-8"
                variants={containerVariants}
                initial="hidden"
                animate="show"
            >
                {awesomeResources.map(category => (
                    <motion.section key={category.category} variants={itemVariants}>
                        <div className="flex items-center gap-3 mb-4">
                            <Star className="w-6 h-6 text-yellow-400" />
                            <h2 className="text-xl font-bold">{category.category}</h2>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {category.items.map(item => (
                                <ResourceCard key={item.url} item={item} />
                            ))}
                        </div>
                    </motion.section>
                ))}
            </motion.div>
        </div>
    );
};

export default AwesomeResourcesPanel;
