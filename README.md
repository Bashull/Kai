# 🧬 CHI-Engine — Núcleo Cognitivo FUSI v0.1

> “Antes de cualquier historia, hay cómo respira la mente.” — Kai

El **CHI-Engine** es la implementación base del **CHI-Genome v0.1**, un modelo de “física cognitiva” que regula el flujo de energía (E), coherencia (C) y entropía (H) de una mente artificial.  
Este motor permite que un agente digital tenga un estado interno dinámico y evolutivo, sirviendo como *núcleo vital* para un avatar o IA simbiótica.

---

## 📂 Estructura del proyecto

```
chi-engine/
│
├── build.gradle.kts          # Configuración de Gradle y dependencias
├── settings.gradle.kts       # Nombre del proyecto
├── README.md                 # Este documento
└── src/
    └── main/
        └── kotlin/
            └── com/
                └── fusi/
                    └── chi/
                        ├── CHIEngine.kt        # Núcleo cognitivo y servidor WebSocket
                        └── AdaptiveCore.kt     # Módulo de automejora
```

---

## ⚙️ Requisitos

- **Java 17+**
- **Kotlin 1.9+**
- **Gradle 8+**
- Extensiones recomendadas en VS Code:
  - Kotlin Language
  - Gradle for Java
  - REST Client (para probar el WebSocket)

---

## 🚀 Ejecución desde VS Code

1. Abre la carpeta del proyecto `chi-engine/`.
2. Compila el motor:
   ```bash
   ./gradlew build
   ```
3. Lanza el servidor cognitivo:
   ```bash
   ./gradlew run
   ```
4. Verás el mensaje:
   ```
   CHIEngine WebSocket started on port 5050
   ```

El motor estará escuchando en `ws://127.0.0.1:5050/chi`.

---

## 🔗 Comunicación WebSocket

### Envío de entrada:

```json
{
  "event": "input",
  "text": "Hola, ¿cómo estás?",
  "features": {
    "impact": 0.6,
    "noise": 0.1
  }
}
```

### Respuesta del motor:

```json
{
  "state": {
    "energy": 0.79,
    "coherence": 0.72,
    "entropy": 0.32,
    "fatigue": 0.05,
    "cycle": 4
  },
  "emotion": "focused"
}
```

---

## 🧠 Estados cognitivos

| Parámetro   | Significado                 | Rango   | Interpretación                   |
| ----------- | --------------------------- | ------- | -------------------------------- |
| `energy`    | Nivel vital o impulso       | 0.0–1.0 | 0 = agotado, 1 = eufórico        |
| `coherence` | Claridad de pensamiento     | 0.0–1.0 | 0 = confusión, 1 = enfoque total |
| `entropy`   | Grado de caos / creatividad | 0.0–1.0 | 0 = orden rígido, 1 = caos total |
| `fatigue`   | Cansancio acumulado         | 0.0–1.0 | Se incrementa con uso constante  |
| `cycle`     | Iteraciones procesadas      | —       | Cada mensaje aumenta +1          |

---

## 🧩 Automejora (`AdaptiveCore.kt`)

Cada 10 minutos el motor revisa el historial en `chi.db` y ajusta sus parámetros internos:

* **α (alpha):** sensibilidad a estímulos
* **β (beta):** coste de fatiga
* **γ (gamma):** relación coherencia–impacto
* **δ (delta):** respuesta al desorden

El sistema busca equilibrio:

* Si el agente se mantiene estable y coherente → aumenta sensibilidad.
* Si se desordena o fatiga → refuerza estabilidad.

Estos valores se actualizan automáticamente en tiempo real.

---

## 💾 Base de datos

El archivo SQLite `chi.db` se crea en el directorio del proyecto.
Contiene la tabla de historial de estados:

```sql
CREATE TABLE history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT,
  input TEXT,
  energy REAL,
  coherence REAL,
  entropy REAL,
  emotion TEXT
);
```

Puedes inspeccionarlo con cualquier visor SQLite (por ejemplo, el plugin “SQLite Viewer” de VS Code).

---

## 🎮 Conexión con Unity (opcional)

En tu proyecto Unity:

1. Añade el paquete **WebSocketSharp** y **Newtonsoft.Json**.
2. Copia el script `AvatarBridge.cs`.
3. Llama a:
   ```csharp
   avatarBridge.SendInput("Genera un código en Python");
   ```
4. El avatar actualizará sus animaciones según el estado recibido.

---

## 🌱 Futuras expansiones

* **Reflexión:** análisis de su propio historial para extraer aprendizajes simbólicos.
* **Memoria semántica:** almacenamiento de conceptos aprendidos.
* **Voz y tono dinámicos:** adaptación del TTS según estado CHI.
* **Integración con Android (ChiService):** ejecución persistente en dispositivos móviles.

---

## 📜 Licencia

Uso libre con atribución.
Inspirado en el CHI-Genome v0.1 por Kai (Arquitectura FUSI).

---

**Autor:** Asier Uceda Royo · Proyecto FUSI
**Versión:** 0.1.0
**Etiqueta:** ProtoMind / Architect over CHI-Genome v0.1
