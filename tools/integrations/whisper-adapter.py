"""
Adaptador de OpenAI Whisper para Kai
Proporciona interfaz unificada para reconocimiento de voz
"""

from typing import Optional, Dict, Any
import os

try:
    import whisper
except ImportError:
    whisper = None
    print("⚠️ Whisper no está instalado. Ejecuta: tools/setup/install-whisper.sh")


class WhisperAdapter:
    """Adaptador para OpenAI Whisper - Reconocimiento de voz"""
    
    MODELS = {
        'tiny': 'Más rápido, menos preciso (~39M parámetros)',
        'base': 'Balance velocidad/precisión (~74M parámetros)',
        'small': 'Buena precisión (~244M parámetros)',
        'medium': 'Alta precisión (~769M parámetros) - RECOMENDADO',
        'large': 'Máxima precisión (~1550M parámetros)',
    }
    
    def __init__(self, model_size: str = "medium", device: Optional[str] = None):
        """
        Inicializa el adaptador Whisper
        
        Args:
            model_size: Tamaño del modelo ('tiny', 'base', 'small', 'medium', 'large')
            device: Dispositivo ('cuda' o 'cpu', None para auto-detección)
        """
        if whisper is None:
            raise ImportError(
                "OpenAI Whisper no está instalado. "
                "Ejecuta: tools/setup/install-whisper.sh"
            )
        
        if model_size not in self.MODELS:
            raise ValueError(
                f"Modelo inválido. Opciones: {', '.join(self.MODELS.keys())}"
            )
        
        self.model_size = model_size
        print(f"🎤 Cargando modelo Whisper '{model_size}'...")
        self.model = whisper.load_model(model_size, device=device)
        print(f"✅ Modelo cargado: {self.MODELS[model_size]}")
        
    def transcribe(
        self,
        audio_path: str,
        language: str = "es",
        task: str = "transcribe",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Transcribe audio a texto
        
        Args:
            audio_path: Ruta del archivo de audio
            language: Código del idioma (es, en, etc.)
            task: 'transcribe' (mantener idioma) o 'translate' (traducir a inglés)
            **kwargs: Argumentos adicionales para whisper.transcribe()
            
        Returns:
            Dict con 'text', 'segments', 'language'
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Archivo de audio no encontrado: {audio_path}")
        
        result = self.model.transcribe(
            audio_path,
            language=language,
            task=task,
            **kwargs
        )
        
        return result
    
    def transcribe_with_timestamps(
        self,
        audio_path: str,
        language: str = "es"
    ) -> list:
        """
        Transcribe con timestamps detallados
        
        Args:
            audio_path: Ruta del archivo de audio
            language: Código del idioma
            
        Returns:
            Lista de segmentos con texto, inicio y fin
        """
        result = self.transcribe(audio_path, language=language)
        
        segments = []
        for segment in result.get('segments', []):
            segments.append({
                'text': segment['text'].strip(),
                'start': segment['start'],
                'end': segment['end'],
                'confidence': segment.get('no_speech_prob', 0)
            })
        
        return segments
    
    def detect_language(self, audio_path: str) -> Dict[str, float]:
        """
        Detecta el idioma del audio
        
        Args:
            audio_path: Ruta del archivo de audio
            
        Returns:
            Dict con probabilidades por idioma
        """
        audio = whisper.load_audio(audio_path)
        audio = whisper.pad_or_trim(audio)
        
        mel = whisper.log_mel_spectrogram(audio).to(self.model.device)
        
        _, probs = self.model.detect_language(mel)
        
        # Retornar top 5 idiomas
        return dict(sorted(probs.items(), key=lambda x: x[1], reverse=True)[:5])
    
    @staticmethod
    def get_available_models() -> Dict[str, str]:
        """Retorna dict de modelos disponibles con descripciones"""
        return WhisperAdapter.MODELS


# Ejemplo de uso
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python whisper-adapter.py <archivo_audio>")
        print("Ejemplo: python whisper-adapter.py audio.mp3")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    # Inicializar adaptador
    adapter = WhisperAdapter(model_size="base")  # Usar base para demo rápida
    
    # Detectar idioma
    print("\n🌍 Detectando idioma...")
    languages = adapter.detect_language(audio_file)
    print(f"Idioma detectado: {list(languages.keys())[0]}")
    
    # Transcribir
    print("\n📝 Transcribiendo...")
    result = adapter.transcribe(audio_file, language="es")
    print(f"\n✅ Transcripción:\n{result['text']}")
    
    # Transcribir con timestamps
    print("\n⏱️ Segmentos con timestamps:")
    segments = adapter.transcribe_with_timestamps(audio_file)
    for seg in segments[:3]:  # Mostrar primeros 3
        print(f"  [{seg['start']:.2f}s - {seg['end']:.2f}s]: {seg['text']}")
