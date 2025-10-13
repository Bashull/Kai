import { GoogleGenAI, FunctionCall } from "@google/genai";
import { GeneratedImage, CodeLanguage, Entity } from "../types";
import { kaiTools } from './kaiTools';
import { apiClient } from './apiClient';


// Initialize the Google AI client
// It is assumed that process.env.API_KEY is configured in the execution environment.
const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

/**
 * Creates a streaming chat session with the Gemini model, with function calling enabled.
 * @param history The chat history to provide context.
 * @param prompt The user's new prompt.
 * @returns An async iterable stream of chat response text chunks.
 */
export const streamChat = async function* (history: { role: string, parts: { text: string }[] }[], prompt: string) {
    const chat = ai.chats.create({
        model: 'gemini-2.5-flash',
        history: history,
        config: {
            tools: [{ functionDeclarations: kaiTools }]
        }
    });

    const result = await chat.sendMessageStream({ message: prompt });

    const functionCalls: FunctionCall[] = [];

    for await (const chunk of result) {
        if (chunk.text) {
            yield chunk.text;
        }
        if (chunk.functionCalls) {
            functionCalls.push(...chunk.functionCalls);
        }
    }

    if (functionCalls.length > 0) {
        yield `\n\n*Llamando herramientas: ${functionCalls.map(fc => fc.name).join(', ')}...*\n\n`;

        const toolResponses = await Promise.all(
            functionCalls.map(async (call) => {
                try {
                    const apiResult = await apiClient[call.name](call.args);
                    return {
                        functionResponse: {
                            name: call.name,
                            response: { result: apiResult },
                        },
                    };
                } catch (e) {
                    console.error(`Error calling tool ${call.name}:`, e);
                    const errorMessage = e instanceof Error ? e.message : 'Unknown error';
                    return {
                        functionResponse: {
                            name: call.name,
                            response: { error: errorMessage },
                        }
                    };
                }
            })
        );

        const finalResult = await chat.sendMessageStream({ parts: toolResponses });

        for await (const chunk of finalResult) {
            if (chunk.text) {
                yield chunk.text;
            }
        }
    }
};


/**
 * Generates content with AI.
 * @param prompt The user's prompt.
 * @returns The text response from the model.
 */
// FIX: Add missing generateWithAI function. - This is now fixed.
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
 * Summarizes a given block of text.
 * @param text The text to summarize.
 * @returns A concise summary of the text.
 */
export const summarizeText = async (text: string): Promise<string> => {
    const prompt = `Por favor, resume el siguiente texto en un párrafo conciso y claro. Captura las ideas y decisiones clave. El resumen debe ser adecuado para ser guardado como un recuerdo a largo plazo.\n\nTexto a resumir:\n"""\n${text}\n"""\n\nResumen:`;
    try {
        const response = await ai.models.generateContent({
            model: 'gemini-2.5-flash',
            contents: prompt,
        });
        return response.text;
    } catch (error) {
        console.error("Summarization failed:", error);
        if (error instanceof Error) {
            throw new Error(error.message);
        }
        throw new Error("An unknown error occurred during text summarization.");
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

/**
 * Performs an AI-powered search based on a user query and Kernel context.
 * @param searchQuery The user's natural language query.
 * @param entities A list of entities from the Kernel for context.
 * @returns A markdown-formatted string with the search results.
 */
export const performAISearch = async (searchQuery: string, entities: Entity[]): Promise<string> => {
    const kernelContext = entities.length > 0
        ? `Here is a list of knowledge entities currently stored in the Kernel:\n${entities.map(e => `- TYPE: ${e.type}, CONTENT: ${e.content.substring(0, 150)}...`).join('\n')}`
        : "The Kernel is currently empty.";

    const prompt = `You are the intelligent search core for KaiOS, a personal AI assistant.
A user has submitted the following query: "${searchQuery}"

${kernelContext}

Analyze the user's query and the Kernel data. Provide a concise and helpful response.
- Leverage semantic understanding to connect related but not explicitly linked concepts from the Kernel.
- If the query can be answered using the Kernel entities, summarize the relevant information.
- If the query seems to be a command or a request to see a specific part of the app (e.g., "show my missions", "I want to create a CV", "open the forge"), suggest which panel the user should navigate to. The available panels are: Chat, Kernel, La Forja, IA Studio, Misiones, Constructor de CV, Ajustes.
- If it's a general knowledge question, provide a direct answer.
- Format your response in clean Markdown. Start with a clear heading for your answer.`;

    try {
        const response = await ai.models.generateContent({
            model: 'gemini-2.5-flash',
            contents: prompt,
        });
        return response.text;
    } catch (error) {
        console.error("AI Search failed:", error);
        if (error instanceof Error) {
            throw new Error(error.message);
        }
        throw new Error("An unknown error occurred during AI search.");
    }
};