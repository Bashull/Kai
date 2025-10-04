import { format, formatDistanceToNow } from 'date-fns';
import enUS from 'date-fns/locale/en-US';
import es from 'date-fns/locale/es';

const locales = { es, en: enUS };

export const formatDate = (date: string | number | Date, locale: keyof typeof locales = 'en'): string => {
  return format(new Date(date), 'dd/MM/yyyy HH:mm', {
    locale: locales[locale]
  });
};

export const formatRelativeTime = (date: string | number | Date, locale: keyof typeof locales = 'en'): string => {
  try {
    return formatDistanceToNow(new Date(date), {
      addSuffix: true,
      locale: locales[locale]
    });
  } catch (e) {
    return 'just now';
  }
};

export const truncateText = (text: string, maxLength: number = 100): string => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

export const generateId = (): string => {
  return Date.now().toString(36) + Math.random().toString(36).substring(2);
};

export const debounce = <F extends (...args: any[]) => any>(func: F, wait: number): ((...args: Parameters<F>) => void) => {
  let timeout: ReturnType<typeof setTimeout> | null;
  return function executedFunction(...args: Parameters<F>) {
    const later = () => {
      timeout = null;
      func(...args);
    };
    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(later, wait);
  };
};

export const throttle = <F extends (...args: any[]) => any>(func: F, limit: number): ((...args: Parameters<F>) => void) => {
  let inThrottle: boolean;
  return function(this: any, ...args: Parameters<F>) {
    const context = this;
    if (!inThrottle) {
      func.apply(context, args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
};

export const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    console.error('Failed to copy text: ', err);
    try {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = "absolute";
        textArea.style.left = "-9999px";
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        return true;
    } catch(fallbackErr) {
        console.error('Fallback copy method failed: ', fallbackErr);
        return false;
    }
  }
};

export const downloadFile = (data: string | Blob, filename: string, type: string = 'text/plain') => {
  const blob = data instanceof Blob ? data : new Blob([data], { type });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export const dataUrlToBlob = async (dataUrl: string): Promise<Blob> => {
    const res = await fetch(dataUrl);
    return await res.blob();
}

export const validateEmail = (email: string): boolean => {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
};

export const validateApiKey = (key: string, service: 'openai' | 'anthropic' | 'stability') => {
  const patterns = {
    openai: /^sk-[a-zA-Z0-9]{48}$/,
    anthropic: /^sk-ant-[a-zA-Z0-9-]{95}$/,
    stability: /^sk-[a-zA-Z0-9]{32}$/
  };
  
  return patterns[service] ? patterns[service].test(key) : key.length > 10;
};

export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

export const getFileExtension = (filename: string): string => {
  return filename.split('.').pop()?.toLowerCase() || '';
};

export const isImageFile = (filename: string): boolean => {
  const imageExtensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'];
  return imageExtensions.includes(getFileExtension(filename));
};

export const generateColorFromString = (str: string): string => {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = hash % 360;
  return `hsl(${hue}, 70%, 50%)`;
};