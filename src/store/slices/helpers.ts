/**
 * Store Helper Functions
 * 
 * Shared utilities for store slices
 */

/**
 * Debounce function for delayed execution
 */
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
};

/**
 * Throttle function for rate limiting
 */
export const throttle = <T extends (...args: any[]) => any>(
  func: T,
  limit: number
): ((...args: Parameters<T>) => void) => {
  let inThrottle: boolean;
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
};

/**
 * Deep clone object
 */
export const deepClone = <T>(obj: T): T => {
  return JSON.parse(JSON.stringify(obj));
};

/**
 * Merge objects deeply
 */
export const deepMerge = <T extends Record<string, any>>(
  target: T,
  source: Partial<T>
): T => {
  const output = { ...target };
  
  Object.keys(source).forEach(key => {
    const sourceValue = source[key as keyof T];
    const targetValue = output[key as keyof T];
    
    if (
      sourceValue &&
      typeof sourceValue === 'object' &&
      !Array.isArray(sourceValue) &&
      targetValue &&
      typeof targetValue === 'object' &&
      !Array.isArray(targetValue)
    ) {
      output[key as keyof T] = deepMerge(targetValue as any, sourceValue as any);
    } else {
      output[key as keyof T] = sourceValue as any;
    }
  });
  
  return output;
};

/**
 * Safe storage operations with error handling
 */
export const safeStorage = {
  get: <T>(key: string, defaultValue: T): T => {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch (error) {
      console.error(`Error reading from localStorage: ${key}`, error);
      return defaultValue;
    }
  },
  
  set: (key: string, value: any): boolean => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (error) {
      console.error(`Error writing to localStorage: ${key}`, error);
      return false;
    }
  },
  
  remove: (key: string): boolean => {
    try {
      localStorage.removeItem(key);
      return true;
    } catch (error) {
      console.error(`Error removing from localStorage: ${key}`, error);
      return false;
    }
  }
};

/**
 * Array operations
 */
export const arrayHelpers = {
  /**
   * Move item in array from one index to another
   */
  move: <T>(arr: T[], from: number, to: number): T[] => {
    const newArr = [...arr];
    const item = newArr.splice(from, 1)[0];
    newArr.splice(to, 0, item);
    return newArr;
  },
  
  /**
   * Toggle item in array
   */
  toggle: <T>(arr: T[], item: T): T[] => {
    const index = arr.indexOf(item);
    if (index > -1) {
      return arr.filter((_, i) => i !== index);
    }
    return [...arr, item];
  },
  
  /**
   * Update item in array by id
   */
  updateById: <T extends { id: string }>(
    arr: T[],
    id: string,
    updates: Partial<T>
  ): T[] => {
    return arr.map(item => 
      item.id === id ? { ...item, ...updates } : item
    );
  }
};

export const StoreHelpers = {
  debounce,
  throttle,
  deepClone,
  deepMerge,
  storage: safeStorage,
  array: arrayHelpers,
};

export default StoreHelpers;
