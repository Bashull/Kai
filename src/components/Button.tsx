import React, { forwardRef, ElementType, ComponentPropsWithRef, ReactNode } from 'react';
import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';

type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'success' | 'kai';
type ButtonSize = 'sm' | 'md' | 'lg' | 'xl';

interface ButtonProps extends Omit<ComponentPropsWithRef<typeof motion.button>, 'children'> {
  children?: ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: ElementType;
  iconPosition?: 'left' | 'right';
  className?: string;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(({
  children,
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  icon: Icon,
  iconPosition = 'left',
  className = '',
  ...props
}, ref) => {
  const baseClasses = 'inline-flex items-center justify-center font-semibold rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-kai-dark disabled:opacity-50 disabled:cursor-not-allowed';
  
  const variants = {
    primary: 'bg-kai-primary hover:bg-indigo-500 text-white focus:ring-kai-primary hover:shadow-lg hover:shadow-indigo-500/30',
    secondary: 'bg-gray-700 hover:bg-gray-600 text-gray-200 focus:ring-gray-500',
    outline: 'border border-border-color hover:bg-kai-surface text-text-primary focus:ring-kai-primary',
    ghost: 'hover:bg-kai-surface text-text-secondary focus:ring-kai-primary',
    danger: 'bg-red-600 hover:bg-red-700 text-white focus:ring-red-500',
    success: 'bg-green-600 hover:bg-green-700 text-white focus:ring-green-500',
    kai: 'bg-kai-green hover:bg-opacity-90 text-black focus:ring-kai-green'
  };
  
  const sizes = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base',
    xl: 'px-8 py-4 text-lg'
  };
  
  const classes = `${baseClasses} ${variants[variant]} ${sizes[size]} ${className}`;
  
  const iconSize = { sm: 14, md: 16, lg: 18, xl: 20 }[size];
  const iconMargin = children ? (iconPosition === 'left' ? 'mr-2' : 'ml-2') : '';

  return (
    <motion.button
      ref={ref}
      whileHover={{ scale: disabled || loading ? 1 : 1.02 }}
      whileTap={{ scale: disabled || loading ? 1 : 0.98 }}
      className={classes}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <Loader2 style={{ width: iconSize, height: iconSize }} className={`animate-spin ${iconMargin}`} />
      ) : (
        Icon && iconPosition === 'left' && <Icon style={{ width: iconSize, height: iconSize }} className={iconMargin} />
      )}
      
      {children}
      
      {!loading && Icon && iconPosition === 'right' && (
        <Icon style={{ width: iconSize, height: iconSize }} className={iconMargin} />
      )}
    </motion.button>
  );
});

Button.displayName = 'Button';

export default Button;