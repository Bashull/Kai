import { GoogleGenAI } from "@google/genai";
import { GeneratedImage, CodeLanguage } from "../types";

// Initialize the Google AI client
// It is assumed that process.env.API_KEY is configured in the execution environment.
const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

/**
 * Creates a streaming chat session with the Gemini model.
 * @param history The chat history to provide context.
 * @param prompt The user's new prompt.
 * @returns An async iterable stream of chat responses.
 */
export const streamChat = async (history: { role: string, parts: { text: string }[] }[], prompt: string) => {
    const chat = ai.chats.create({
        model: 'gemini-2.5-flash',
        history: history,
    });
    return chat.sendMessageStream({ message: prompt });
};

/**
 * Generates content with AI.
 * @param prompt The user's prompt.
 * @returns The text response from the model.
 */
// FIX: Add missing generateWithAI function.
export const generateWithAI = async (prompt: string): Promise<string> => {
    try {
        const response = await ai.models.generateContent({
            model: 'gemini-2.5-flash',
            contents: prompt,
        });
        return response.text;
    } catch (error) {
        console.error("AI Generation failed:", error);
        if (error instanceof Error) {
            return `Error: ${error.message}`;
        }
        return "An unknown error occurred during AI generation.";
    }
};

/**
 * Performs a simple check to verify API access and model functionality.
 * Sends a 'ping' and expects a 'pong'.
 * @returns The text response from the model.
 */
export const checkAIAccess = async (): Promise<string> => {
    try {
        const response = await ai.models.generateContent({
            model: 'gemini-2.5-flash',
            contents: "Respond with only the word 'PONG'. Nothing else.",
            config: {
                temperature: 0,
            }
        });
        return response.text;
    } catch (error) {
        console.error("AI Access Check Failed:", error);
        if (error instanceof Error) {
            return `ERROR: ${error.message}`;
        }
        return "ERROR: An unknown error occurred.";
    }
};

/**
 * Generates a code snippet.
 * @param prompt The description of the code to generate.
 * @param language The programming language.
 * @returns The generated code as a string.
 */
export const generateCode = async (prompt: string, language: CodeLanguage): Promise<string> => {
    const fullPrompt = `Generate a code snippet for the following request in ${language}.\n\nRequest: "${prompt}"\n\nProvide only the code, without any extra explanation or markdown formatting. If you need to add comments, use the language's comment syntax.`;
    try {
        const response = await ai.models.generateContent({
            model: 'gemini-2.5-flash',
            contents: fullPrompt,
        });
        // The model might still wrap the code in markdown, so let's clean it up.
        const text = response.text;
        const codeBlockRegex = new RegExp("```" + language + "?\\n([\\s\\S]*?)\\n```", "s");
        const match = text.match(codeBlockRegex);
        return match ? match[1] : text.replace(/^```(?:\w+\n)?/, '').replace(/```$/, '');
    } catch (error) {
        console.error("Code Generation failed:", error);
        if (error instanceof Error) {
            return `// Error generating code: ${error.message}`;
        }
        return "// An unknown error occurred during code generation.";
    }
};

/**
 * Generates images from a text prompt.
 * @param prompt The description of the image to generate.
 * @returns An array of generated image objects with URL and prompt.
 */
export const generateImages = async (prompt: string): Promise<GeneratedImage[]> => {
    try {
        const response = await ai.models.generateImages({
            model: 'imagen-4.0-generate-001',
            prompt: prompt,
            config: {
                numberOfImages: 1,
                outputMimeType: 'image/png',
                aspectRatio: '1:1',
            },
        });

        if (!response.generatedImages || response.generatedImages.length === 0) {
            throw new Error("No images were generated.");
        }

        return response.generatedImages.map(img => ({
            prompt: prompt,
            url: `data:image/png;base64,${img.image.imageBytes}`
        }));
    } catch (error) {
        console.error("Image Generation failed:", error);
        // Propagate the error to be handled by the UI
        throw error;
    }
};