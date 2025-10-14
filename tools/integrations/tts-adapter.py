"""
Adaptador de Coqui TTS para Kai
Proporciona interfaz unificada para síntesis de voz
"""

from typing import Optional, Dict, Any
import os
from pathlib import Path

try:
    from TTS.api import TTS
except ImportError:
    TTS = None
    print("⚠️ Coqui TTS no está instalado. Ejecuta: tools/setup/install-tts.sh")


class TTSAdapter:
    """Adaptador para Coqui TTS con modelos en español e inglés"""
    
    def __init__(
        self, 
        model_name: str = "tts_models/es/css10/vits",
        device: str = "cpu"
    ):
        """
        Inicializa el adaptador TTS
        
        Args:
            model_name: Nombre del modelo TTS a usar
            device: Dispositivo ('cpu' o 'cuda')
        """
        if TTS is None:
            raise ImportError(
                "Coqui TTS no está instalado. "
                "Ejecuta: tools/setup/install-tts.sh"
            )
        
        self.model_name = model_name
        self.device = device
        self.tts = TTS(model_name=model_name, progress_bar=False).to(device)
        
    def speak(
        self, 
        text: str, 
        output_path: Optional[str] = None,
        speaker: Optional[str] = None,
        language: Optional[str] = None
    ) -> str:
        """
        Convierte texto a voz
        
        Args:
            text: Texto a sintetizar
            output_path: Ruta donde guardar el audio (si es None, usa temporal)
            speaker: ID del speaker (para modelos multi-speaker)
            language: Idioma (para modelos multi-idioma)
            
        Returns:
            Ruta del archivo de audio generado
        """
        if output_path is None:
            output_path = "/tmp/kai_speech.wav"
        
        # Preparar kwargs según capacidades del modelo
        kwargs: Dict[str, Any] = {}
        if speaker and hasattr(self.tts, 'speakers'):
            kwargs['speaker'] = speaker
        if language and hasattr(self.tts, 'languages'):
            kwargs['language'] = language
            
        # Generar audio
        self.tts.tts_to_file(text=text, file_path=output_path, **kwargs)
        
        return output_path
    
    def list_available_speakers(self) -> list:
        """Retorna lista de speakers disponibles"""
        if hasattr(self.tts, 'speakers') and self.tts.speakers:
            return self.tts.speakers
        return []
    
    def list_available_languages(self) -> list:
        """Retorna lista de idiomas disponibles"""
        if hasattr(self.tts, 'languages') and self.tts.languages:
            return self.tts.languages
        return []
    
    @staticmethod
    def list_models() -> list:
        """Lista todos los modelos TTS disponibles"""
        if TTS is None:
            return []
        return TTS.list_models()


# Ejemplo de uso
if __name__ == "__main__":
    # Inicializar adaptador
    adapter = TTSAdapter()
    
    # Generar voz
    print("🔊 Generando voz de Kai...")
    audio_file = adapter.speak(
        "Hola, soy Kai, tu compañero virtual. ¿En qué puedo ayudarte hoy?",
        output_path="kai_greeting.wav"
    )
    print(f"✅ Audio generado: {audio_file}")
    
    # Listar modelos disponibles
    print("\n📋 Modelos disponibles:")
    for model in TTSAdapter.list_models()[:5]:
        print(f"  - {model}")
