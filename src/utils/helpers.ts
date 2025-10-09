import { formatDistanceToNow, format } from 'date-fns';
import { es } from 'date-fns/locale';

export const formatRelativeTime = (date: string | number | Date): string => {
  try {
    return formatDistanceToNow(new Date(date), {
      addSuffix: true,
      locale: es,
    });
  } catch (e) {
    return 'hace un momento';
  }
};

export const generateId = (): string => {
  return Date.now().toString(36) + Math.random().toString(36).substring(2);
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

export const downloadFile = (data: string | Blob, filename: string) => {
  const blob = data instanceof Blob ? data : new Blob([data], { type: 'text/plain' });
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
