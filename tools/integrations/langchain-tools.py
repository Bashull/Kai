"""
Herramientas LangChain para Kai
Integración de cadenas de razonamiento y memoria
"""

from typing import List, Dict, Any, Optional
import os

try:
    from langchain.chains import LLMChain, ConversationChain
    from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
    from langchain.prompts import PromptTemplate
    from langchain.agents import Tool, AgentExecutor, create_react_agent
except ImportError:
    print("⚠️ LangChain no está instalado. Instala con: pip install langchain")
    LLMChain = None


class KaiLangChainTools:
    """Herramientas LangChain para orquestación de Kai"""
    
    def __init__(self, llm=None):
        """
        Inicializa herramientas LangChain
        
        Args:
            llm: Modelo de lenguaje (OpenAI, Gemini, etc.)
        """
        if LLMChain is None:
            raise ImportError("LangChain no está instalado")
        
        self.llm = llm
        self.memory = ConversationBufferMemory(return_messages=True)
        
    def create_conversation_chain(
        self,
        system_prompt: Optional[str] = None
    ) -> ConversationChain:
        """
        Crea una cadena de conversación con memoria
        
        Args:
            system_prompt: Prompt del sistema (personalidad de Kai)
            
        Returns:
            ConversationChain configurada
        """
        if system_prompt is None:
            system_prompt = """
            Eres Kai, un compañero virtual avanzado especializado en Dungeons & Dragons
            y asistencia general. Eres amigable, servicial y te encanta ayudar a crear
            historias épicas de D&D. Tienes memoria a largo plazo y puedes recordar
            preferencias y detalles de sesiones anteriores.
            """
        
        chain = ConversationChain(
            llm=self.llm,
            memory=self.memory,
            verbose=False
        )
        
        return chain
    
    def create_dnd_campaign_chain(self) -> LLMChain:
        """
        Crea una cadena especializada para generar campañas D&D
        
        Returns:
            LLMChain para generación de campañas
        """
        template = """
        Eres el Dungeon Master de una campaña de Dungeons & Dragons 5e.
        
        Contexto de la campaña:
        {campaign_context}
        
        Personajes:
        {characters}
        
        Situación actual:
        {current_situation}
        
        Genera la siguiente escena de la aventura, incluyendo:
        1. Descripción narrativa inmersiva
        2. Posibles acciones para los jugadores
        3. Consecuencias potenciales
        4. Elementos de D&D (tiradas, habilidades relevantes)
        
        Respuesta del DM:
        """
        
        prompt = PromptTemplate(
            input_variables=["campaign_context", "characters", "current_situation"],
            template=template
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        return chain
    
    def create_memory_rag_chain(self, retriever) -> Any:
        """
        Crea una cadena RAG para búsqueda en memoria de Kai
        
        Args:
            retriever: Retriever de LangChain (conectado a FAISS/Chroma)
            
        Returns:
            Cadena configurada para RAG
        """
        try:
            from langchain.chains import RetrievalQA
        except ImportError:
            raise ImportError("Instala langchain con: pip install langchain")
        
        chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True
        )
        
        return chain
    
    def create_agent_with_tools(self, tools: List[Tool]) -> AgentExecutor:
        """
        Crea un agente con herramientas personalizadas
        
        Args:
            tools: Lista de herramientas disponibles para el agente
            
        Returns:
            AgentExecutor configurado
        """
        from langchain.agents import initialize_agent, AgentType
        
        agent = initialize_agent(
            tools=tools,
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=False,
            memory=self.memory
        )
        
        return agent
    
    @staticmethod
    def create_kai_tools() -> List[Tool]:
        """
        Crea herramientas predefinidas de Kai
        
        Returns:
            Lista de herramientas Tool
        """
        def get_kai_memories(query: str) -> str:
            """Busca en la memoria de Kai"""
            # Aquí conectar con FAISS o base de datos
            return f"Buscando recuerdos sobre: {query}"
        
        def roll_dice(dice_notation: str) -> str:
            """Lanza dados de D&D (ej: 2d6+3)"""
            import re
            import random
            
            match = re.match(r'(\d+)d(\d+)([+-]\d+)?', dice_notation)
            if not match:
                return "Formato inválido. Usa: XdY+Z (ej: 2d6+3)"
            
            num_dice = int(match.group(1))
            die_size = int(match.group(2))
            modifier = int(match.group(3) or 0)
            
            rolls = [random.randint(1, die_size) for _ in range(num_dice)]
            total = sum(rolls) + modifier
            
            return f"🎲 {dice_notation}: {rolls} = {sum(rolls)} {'+' if modifier >= 0 else ''}{modifier if modifier != 0 else ''} = {total}"
        
        def get_dnd_rule(rule_query: str) -> str:
            """Obtiene información sobre reglas de D&D 5e"""
            # Aquí conectar con base de conocimientos de D&D
            return f"Buscando regla: {rule_query}"
        
        tools = [
            Tool(
                name="KaiMemory",
                func=get_kai_memories,
                description="Busca en la memoria de Kai para encontrar información sobre sesiones anteriores, preferencias del usuario, o detalles de personajes"
            ),
            Tool(
                name="DiceRoller",
                func=roll_dice,
                description="Lanza dados de D&D. Formato: XdY+Z (ej: 2d6+3, 1d20, 4d6-2)"
            ),
            Tool(
                name="DnDRules",
                func=get_dnd_rule,
                description="Busca información sobre reglas de Dungeons & Dragons 5e"
            )
        ]
        
        return tools
    
    def summarize_conversation(self) -> str:
        """
        Resume la conversación actual usando la memoria
        
        Returns:
            Resumen de la conversación
        """
        messages = self.memory.chat_memory.messages
        
        if not messages:
            return "No hay conversación para resumir"
        
        summary = f"Conversación con {len(messages)} mensajes:\n"
        for msg in messages[-5:]:  # Últimos 5 mensajes
            role = "Usuario" if msg.type == "human" else "Kai"
            summary += f"- {role}: {msg.content[:100]}...\n"
        
        return summary


# Ejemplo de uso
if __name__ == "__main__":
    print("🔗 Herramientas LangChain para Kai")
    print("=" * 50)
    
    # Crear herramientas de Kai
    tools = KaiLangChainTools.create_kai_tools()
    
    print("\n🛠️ Herramientas disponibles:")
    for tool in tools:
        print(f"\n  📌 {tool.name}")
        print(f"     {tool.description}")
    
    # Probar lanzamiento de dados
    print("\n\n🎲 Probando lanzamiento de dados:")
    dice_tool = tools[1]
    print(dice_tool.func("2d6+3"))
    print(dice_tool.func("1d20"))
    print(dice_tool.func("4d6"))
    
    print("\n✅ Herramientas LangChain listas para integrarse con Kai")
