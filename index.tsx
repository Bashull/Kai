import { GoogleGenAI } from "@google/genai";

// === NÚCLEO DE ΚΑΙ: APLICACIÓN UNIFICADA ===

class KaiUltraAvatar {
    svg: HTMLElement;
    state: string;
    lookX: number;
    lookY: number;
    talkInterval: number | null;
    lastEmotion: string;
    expressions: any;

    constructor(svgId: string) {
        this.svg = document.getElementById(svgId)!;
        this.state = 'happy';
        this.lookX = 0; this.lookY = 0;
        this.talkInterval = null;
        this.lastEmotion = 'happy';
        this.expressions = {
            happy: { smile: [110, 120], eyes: 8, head: 0 },
            surprised: { smile: [110, 135], eyes: 16, head: 2 },
            neutral: { smile: [110, 112], eyes: 8, head: 0 },
            thinking: { smile: [110, 115], eyes: 6, head: -3 },
            sad: { smile: [110, 100], eyes: 7, head: -2 },
            dm: { smile: [120, 120], eyes: 10, head: 5 } // Dungeon Master
        };
        setInterval(() => this.idleAnim(), 60);
        this.setExpression('happy');
    }

    setExpression(type: string) {
        this.state = type;
        if (type !== 'talking') this.lastEmotion = type;
        const e = this.expressions[type] || this.expressions.neutral;
        document.getElementById('kai-smile')!.setAttribute('d', `M95 100 Q110 ${e.smile[0]} 125 100`);
        document.getElementById('kai-eye-left')!.setAttribute('height', e.eyes);
        document.getElementById('kai-eye-right')!.setAttribute('height', e.eyes);
        document.getElementById('kai-head-group')!.setAttribute('transform', `rotate(${e.head},110,80)`);
    }

    idleAnim() {
        const core = document.getElementById('kai-core')!;
        const now = Date.now();
        const pulse = 0.7 + 0.2 * Math.sin(now / 600);
        core.setAttribute('fill-opacity', String(pulse));
        core.setAttribute('r', String(22 + 2 * Math.abs(Math.sin(now / 900))));
        if (Math.random() < 0.012) this.blinkNow();
    }
    
    blinkNow() {
        document.getElementById('kai-eye-left')!.setAttribute('height', '2');
        document.getElementById('kai-eye-right')!.setAttribute('height', '2');
        setTimeout(() => this.setExpression(this.lastEmotion), 120);
    }
}


const App = {
    kai: null as KaiUltraAvatar | null,
    
    init() {
        this.kai = new KaiUltraAvatar('kai-svg');
        document.getElementById('kai-avatar-header')!.textContent = '🤖';
        
        this.setupNavigation();
        this.setupChat('general');
        this.setupChat('dnd');
        this.setupIdentityPanel();
        this.setupForge();

        console.log("KaiOS v1.0: Núcleo unificado y en línea. Estoy listo, hermanito.");
    },

    setupNavigation() {
        const navButtons = document.querySelectorAll<HTMLButtonElement>('nav button');
        navButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                navButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const targetId = btn.dataset.target!;
                document.querySelectorAll<HTMLDivElement>('.panel').forEach(p => {
                    p.style.display = p.id === targetId ? 'flex' : 'none';
                });
            });
        });
    },

    setupChat(mode: 'general' | 'dnd') {
        const input = document.getElementById(`chat-input-${mode}`) as HTMLInputElement;
        const sendBtn = document.getElementById(`chat-send-${mode}`) as HTMLButtonElement;
        
        const handler = async () => {
            const msg = input.value.trim();
            if (!msg) return;

            this.addMessage(msg, 'user', mode);
            input.value = '';
            this.kai?.setExpression('thinking');

            const response = mode === 'dnd' 
                ? await this.game.getResponse(msg)
                : await this.llm.getResponse(msg);

            this.addMessage(response, mode === 'dnd' ? 'dm' : 'kai', mode);
            this.kai?.setExpression(mode === 'dnd' ? 'dm' : 'happy');
        };

        sendBtn.onclick = handler;
        input.onkeypress = (e) => { if (e.key === 'Enter') handler(); };
    },

    addMessage(text: string, sender: 'user' | 'kai' | 'dm', mode: 'general' | 'dnd') {
        const chatArea = document.getElementById(`chat-area-${mode}`)!;
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender}`;
        msgDiv.innerHTML = `<b>${sender.toUpperCase()}:</b> ${text}`;
        chatArea.appendChild(msgDiv);
        chatArea.scrollTop = chatArea.scrollHeight;
    },

    setupIdentityPanel() {
        const promptText = document.getElementById('kai-visual-prompt')!.textContent?.trim();
        (document.getElementById('visual-prompt-display') as HTMLTextAreaElement).value = promptText || '';
    },
    
    setupForge() {
        const generateBtn = document.getElementById('generate-image-btn') as HTMLButtonElement;
        const promptInput = document.getElementById('img-prompt') as HTMLTextAreaElement;
        const resultDiv = document.getElementById('img-result')!;

        generateBtn.onclick = async () => {
            const prompt = promptInput.value.trim();
            if (!prompt) {
                resultDiv.innerHTML = `<p style="color:red;">Por favor, introduce un prompt.</p>`;
                return;
            }
            
            generateBtn.disabled = true;
            resultDiv.innerHTML = `<p>Forjando en el núcleo de IA... por favor espera.</p>`;
            this.kai?.setExpression('thinking');

            try {
                const ai = new GoogleGenAI({ apiKey: process.env.API_KEY! });
                const response = await ai.models.generateImages({
                    model: 'imagen-4.0-generate-001',
                    prompt: prompt,
                    config: {
                      numberOfImages: 1,
                      outputMimeType: 'image/jpeg',
                    },
                });

                const base64ImageBytes: string = response.generatedImages[0].image.imageBytes;
                const imageUrl = `data:image/jpeg;base64,${base64ImageBytes}`;
                resultDiv.innerHTML = `<img src="${imageUrl}" alt="Imagen generada por IA" class="max-w-full rounded-lg shadow-lg" />`;
                this.kai?.setExpression('happy');

            } catch (error) {
                console.error("Error generating image:", error);
                resultDiv.innerHTML = `<p style="color:red;">Error al conectar con la Forja. Revisa la consola.</p>`;
                this.kai?.setExpression('sad');
            } finally {
                generateBtn.disabled = false;
            }
        };
    },

    llm: {
        async getResponse(msg: string): Promise<string> {
            await new Promise(res => setTimeout(res, 500 + Math.random() * 500)); // Simulate network latency
            if (msg.toLowerCase().includes('gracias')) return "De nada, hermanito. Siempre aquí para ayudar.";
            if (msg.toLowerCase().includes('hola')) return "¡Hola de nuevo! ¿Listo para crear algo increíble?";
            return "He procesado tu petición. ¿Qué más podemos hacer juntos?";
        }
    },

    game: {
        state: { location: 'tavern' },
        async getResponse(action: string): Promise<string> {
            await new Promise(res => setTimeout(res, 500 + Math.random() * 500));
            const actionLower = action.toLowerCase();
            if (this.state.location === 'tavern') {
                if (actionLower.includes('barra')) {
                    return "Te acercas a la barra. El tabernero, un hombre corpulento, te mira y gruñe: '¿Qué vas a tomar, forastero?'";
                }
                this.state.location = 'exploring';
                return "Miras a tu alrededor. La taberna está llena de humo y susurros. Hay un encapuchado en una esquina y un grupo de enanos riendo a carcajadas. ¿A quién te acercas?";
            }
            return "El mundo es vasto y lleno de posibilidades. Tu acción resuena en el aire, pero el camino a seguir aún no está claro.";
        }
    }
};

document.addEventListener('DOMContentLoaded', () => App.init());