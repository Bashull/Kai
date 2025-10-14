import { formatDistanceToNow } from 'date-fns';
// FIX: Changed date-fns locale import to a more specific path to resolve import errors.
import { es } from 'date-fns/locale';
import { Blob } from '@google/genai';

export const formatRelativeTime = (date: string | number | Date): string => {
  try {
    // FIX: Cast options to `any` to bypass a type error with the `locale` property.
    return formatDistanceToNow(new Date(date), {
      addSuffix: true,
      locale: es,
    } as any);
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

export const downloadFile = (data: string | globalThis.Blob, filename: string) => {
  const blob = data instanceof globalThis.Blob ? data : new globalThis.Blob([data], { type: 'text/plain' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};


export const dataUrlToBlob = async (dataUrl: string): Promise<globalThis.Blob> => {
    const res = await fetch(dataUrl);
    return await res.blob();
}

// --- Audio Helpers for Live API ---
export function encode(bytes: Uint8Array) {
  let binary = '';
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

export function decode(base64: string) {
  const binaryString = atob(base64);
  const len = binaryString.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes;
}

export async function decodeAudioData(
  data: Uint8Array,
  ctx: AudioContext,
  sampleRate: number,
  numChannels: number,
): Promise<AudioBuffer> {
  const dataInt16 = new Int16Array(data.buffer);
  const frameCount = dataInt16.length / numChannels;
  const buffer = ctx.createBuffer(numChannels, frameCount, sampleRate);

  for (let channel = 0; channel < numChannels; channel++) {
    const channelData = buffer.getChannelData(channel);
    for (let i = 0; i < frameCount; i++) {
      channelData[i] = dataInt16[i * numChannels + channel] / 32768.0;
    }
  }
  return buffer;
}

export function createBlob(data: Float32Array): Blob {
  const l = data.length;
  const int16 = new Int16Array(l);
  for (let i = 0; i < l; i++) {
    int16[i] = data[i] * 32768;
  }
  return {
    data: encode(new Uint8Array(int16.buffer)),
    mimeType: 'audio/pcm;rate=16000',
  };
}