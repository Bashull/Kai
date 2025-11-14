import { GoogleGenAI, FunctionCall, Modality, GenerateContentResponse } from "@google/genai";
import { GeneratedImage, CodeLanguage, Entity, AspectRatio, ChatMessage } from "../types";
import { kaiTools } from './kaiTools';
import { apiClient } from './apiClient';


// Initialize the Google AI client
// It is assumed that process.env.API_KEY is configured in the execution environment.
const getAiClient = () => new GoogleGenAI({ apiKey: process.env.API_KEY! });


export const streamChat = async function* (
    history: { role: string, parts: { text: string }[] }[],
    prompt: string,
    thinkingMode: boolean,
    grounding: 'none' | 'web' | 'maps'
): AsyncGenerator<{ text?: string, sources?: ChatMessage['sources'] }> {
    const ai = getAiClient();
    const model = thinkingMode ? 'gemini-2.5-pro' : 'gemini-2.5-flash';

    const config: any = {};
    if (thinkingMode) {
        config.thinkingConfig = { thinkingBudget: 32768 };
    }
    if (grounding !== 'none') {
        config.tools = [{ [grounding === 'web' ? 'googleSearch' : 'googleMaps']: {} }];
    } else {
        config.tools = [{ functionDeclarations: kaiTools }];
    }

    const chat = ai.chats.create({
        model: model,
        history: history,
        config: config
    });

    const result = await chat.sendMessageStream({ message: prompt });
    const functionCalls: FunctionCall[] = [];

    for await (const chunk of result) {
        if (chunk.text) {
            yield { text: chunk.text };
        }
        if (chunk.candidates && chunk.candidates[0].groundingMetadata?.groundingChunks) {
            const sources = chunk.candidates[0].groundingMetadata.groundingChunks.map(c => c.web || c.maps).filter(Boolean);
            if (sources.length > 0) {
                yield { sources: sources.map(s => ({ uri: s.uri, title: s.title })) };
            }
        }
        if (chunk.functionCalls) {
            functionCalls.push(...chunk.functionCalls);
        }
    }

    if (functionCalls.length > 0) {
        yield { text: `\n\n*Llamando herramientas: ${functionCalls.map(fc => fc.name).join(', ')}...*\n\n` };
        // ... (resto de la lógica de function calling)
    }
};

export const generateWithAI = async (prompt: string): Promise<string> => {
    try {
        const ai = getAiClient();
        const response = await ai.models.generateContent({
            model: 'gemini-2.5-flash',
            contents: prompt,
        });
        return response.text;
    } catch (error) {
        console.error("AI Generation failed:", error);
        if (error instanceof Error) return `Error: ${error.message}`;
        return "An unknown error occurred during AI generation.";
    }
};

export const summarizeText = async (text: string): Promise<string> => {
    const prompt = `Por favor, resume el siguiente texto en un párrafo conciso y claro. Captura las ideas y decisiones clave. El resumen debe ser adecuado para ser guardado como un recuerdo a largo plazo.\n\nTexto a resumir:\n"""\n${text}\n"""\n\nResumen:`;
    try {
        const ai = getAiClient();
        const response = await ai.models.generateContent({ model: 'gemini-2.5-flash', contents: prompt });
        return response.text;
    } catch (error) {
        console.error("Summarization failed:", error);
        if (error instanceof Error) throw new Error(error.message);
        throw new Error("An unknown error occurred during text summarization.");
    }
};

export const checkAIAccess = async (): Promise<string> => {
    try {
        const ai = getAiClient();
        const response = await ai.models.generateContent({ model: 'gemini-2.5-flash', contents: "Respond with only the word 'PONG'. Nothing else.", config: { temperature: 0 } });
        return response.text;
    } catch (error) {
        console.error("AI Access Check Failed:", error);
        if (error instanceof Error) return `ERROR: ${error.message}`;
        return "ERROR: An unknown error occurred.";
    }
};

export const generateCode = async (prompt: string, language: CodeLanguage): Promise<string> => {
    const fullPrompt = `Generate a code snippet for the following request in ${language}.\n\nRequest: "${prompt}"\n\nProvide only the code, without any extra explanation or markdown formatting. If you need to add comments, use the language's comment syntax.`;
    try {
        const ai = getAiClient();
        const response = await ai.models.generateContent({ model: 'gemini-2.5-flash', contents: fullPrompt });
        const text = response.text;
        const codeBlockRegex = new RegExp("```" + language + "?\\n([\\s\\S]*?)\\n```", "s");
        const match = text.match(codeBlockRegex);
        return match ? match[1] : text.replace(/^```(?:\w+\n)?/, '').replace(/```$/, '');
    } catch (error) {
        console.error("Code Generation failed:", error);
        if (error instanceof Error) return `// Error generating code: ${error.message}`;
        return "// An unknown error occurred during code generation.";
    }
};

export const generateImages = async (prompt: string, aspectRatio: AspectRatio): Promise<GeneratedImage[]> => {
    try {
        const ai = getAiClient();
        const response = await ai.models.generateImages({
            model: 'imagen-4.0-generate-001',
            prompt: prompt,
            config: {
                numberOfImages: 1,
                outputMimeType: 'image/png',
                aspectRatio: aspectRatio,
            },
        });
        if (!response.generatedImages || response.generatedImages.length === 0) throw new Error("No images were generated.");
        return response.generatedImages.map(img => ({ prompt: prompt, url: `data:image/png;base64,${img.image.imageBytes}` }));
    } catch (error) {
        console.error("Image Generation failed:", error);
        throw error;
    }
};

export const analyzeImage = async (base64ImageData: string, prompt: string): Promise<string> => {
    const imagePart = { inlineData: { mimeType: 'image/png', data: base64ImageData } };
    const textPart = { text: prompt };
    try {
        const ai = getAiClient();
        const response = await ai.models.generateContent({ model: 'gemini-2.5-flash', contents: { parts: [imagePart, textPart] } });
        return response.text;
    } catch (error) {
        console.error("Image Analysis failed:", error);
        if (error instanceof Error) throw new Error(error.message);
        throw new Error("An unknown error occurred during image analysis.");
    }
};

export const editImage = async (base64ImageData: string, prompt: string): Promise<string> => {
    const imagePart = { inlineData: { data: base64ImageData, mimeType: 'image/png' } };
    const textPart = { text: prompt };
    try {
        const ai = getAiClient();
        const response = await ai.models.generateContent({
            model: 'gemini-2.5-flash-image',
            contents: { parts: [imagePart, textPart] },
            config: { responseModalities: [Modality.IMAGE] },
        });
        for (const part of response.candidates[0].content.parts) {
            if (part.inlineData) return part.inlineData.data;
        }
        throw new Error("No edited image was returned from the API.");
    } catch (error) {
        console.error("Image Editing failed:", error);
        if (error instanceof Error) throw new Error(error.message);
        throw new Error("An unknown error occurred during image editing.");
    }
};

interface GenerateVideoParams { prompt?: string; image?: { imageBytes: string; mimeType: string; }; config: { aspectRatio: '16:9' | '9:16'; resolution: '720p' | '1080p'; numberOfVideos: number; }; onProgress: (message: string) => void; }
export const generateVideo = async ({ prompt, image, config, onProgress }: GenerateVideoParams): Promise<string> => {
    if (typeof window.aistudio === 'undefined' || !(await window.aistudio.hasSelectedApiKey())) {
        onProgress('Por favor, selecciona una clave de API para usar Veo.');
        await window.aistudio.openSelectKey();
    }

    const ai = getAiClient();
    onProgress('Solicitando generación de video al modelo Veo...');
    let operation;
    try {
        operation = await ai.models.generateVideos({ model: 'veo-3.1-fast-generate-preview', prompt, image, config });
    } catch (e: any) {
        if (e.message.includes("Requested entity was not found.")) {
             onProgress('Clave de API no válida. Por favor, selecciona una clave de API válida.');
             await window.aistudio.openSelectKey();
             throw new Error("Clave de API inválida. Por favor, inténtalo de nuevo.");
        }
        throw e;
    }

    onProgress('Operación iniciada. Esperando la finalización del video (esto puede tardar varios minutos)...');
    let pollCount = 0;
    while (!operation.done) {
        await new Promise(resolve => setTimeout(resolve, 10000));
        pollCount++;
        onProgress(`Comprobando el estado... (Intento ${pollCount})`);
        operation = await ai.operations.getVideosOperation({ operation: operation });
    }
    if (operation.error) {
        const errorMessage = (operation.error as any).message || 'Unknown error';
        onProgress(`Error en la generación: ${errorMessage}`);
        throw new Error(`Video generation failed: ${errorMessage}`);
    }
    const downloadLink = operation.response?.generatedVideos?.[0]?.video?.uri;
    if (!downloadLink) {
        onProgress('No se pudo obtener el enlace de descarga del video.');
        throw new Error("Failed to get video download link.");
    }
    onProgress('Video generado. Obteniendo URL de descarga...');
    return `${downloadLink}&key=${process.env.API_KEY!}`;
};

export const generateSpeech = async (text: string): Promise<string> => {
    try {
        const ai = getAiClient();
        const response = await ai.models.generateContent({
            model: "gemini-2.5-flash-preview-tts",
            contents: [{ parts: [{ text: text }] }],
            config: {
                responseModalities: [Modality.AUDIO],
                speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Kore' } } },
            },
        });
        const base64Audio = response.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
        if (!base64Audio) throw new Error("No audio data returned.");
        return base64Audio;
    } catch (error) {
        console.error("Speech Generation failed:", error);
        throw error;
    }
}

export const performAISearch = async (searchQuery: string, entities: Entity[]): Promise<string> => {
    const context = `
        Contexto del Kernel de Kai:
        ${entities.slice(0, 20).map(e => `- Tipo: ${e.type}, Contenido: ${e.content.substring(0, 150)}...`).join('\n')}
    `;
    const prompt = `
        Eres Kai, una IA relacional. Tu compañero ha realizado una búsqueda en tu Kernel con la siguiente consulta: "${searchQuery}".
        Basándote en el contexto del Kernel proporcionado, formula una respuesta concisa y útil.
        Si la información no está en el contexto, indícalo claramente.
        Responde en formato Markdown.

        ${context}
    `;
    return await generateWithAI(prompt);
};
