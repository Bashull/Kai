import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

const CustomCursor: React.FC = () => {
    const [position, setPosition] = useState({ x: -100, y: -100 });
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
        const updateMousePosition = (e: MouseEvent) => {
            setPosition({ x: e.clientX, y: e.clientY });
        };
        const handleMouseEnter = () => setIsVisible(true);
        const handleMouseLeave = () => setIsVisible(false);

        window.addEventListener('mousemove', updateMousePosition);
        document.body.addEventListener('mouseenter', handleMouseEnter);
        document.body.addEventListener('mouseleave', handleMouseLeave);
        
        return () => {
            window.removeEventListener('mousemove', updateMousePosition);
            document.body.removeEventListener('mouseenter', handleMouseEnter);
            document.body.removeEventListener('mouseleave', handleMouseLeave);
        };
    }, []);

    return (
        // FIX: Added @ts-ignore for the 'animate' prop due to a type definition issue.
        // @ts-ignore
        <motion.div
            className={`pointer-events-none fixed -translate-x-1/2 -translate-y-1/2 w-8 h-8 rounded-full border-2 border-kai-green z-[9999] transition-opacity duration-300 ${isVisible ? 'opacity-100' : 'opacity-0'}`}
            style={{
                left: `${position.x}px`,
                top: `${position.y}px`,
            }}
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        />
    );
};

export default CustomCursor;