# Ruta a skills existentes en Termux (17-10-2026)

La inspección actual confirmó estas capacidades en `~/.agents/skills`; no se copian ni modifican:

| Trigger | Skill ya existente | Por qué invocarla |
|---|---|---|
| Generación, edición o upscaling de imagen | `kai-image-forge-unified` | Bibliotecas, SHA-256, activos, Zero Spend, providers y QA local |
| Aceptación real de medios generativos | `independent-generative-qa-gates` | Evita autocalificación del generador y conserva artefactos PENDING_QA |
| Comparación de Wan, Hunyuan, LTX u otro backend | `multimedia-provider-benchmark` | Inputs congelados, VRAM, costes, calidad y fallos observados |
| Uso de modelos/datasets de Hugging Face | `model-license-boundary-governance` | Separar licencia de código, pesos, datasets y servicio |
| Nuevo repositorio Github donante | `repository-donor-extraction` | ADN, dependencias, compatibilidad, decisiones ABSORB/ADAPTER/REFERENCE/REJECT |

Estas son **dependencias optativas de workflow**, no imports obligatorios ni evidencia de que los providers funcionan. El Director construye contrato de producción y coordina, nunca clona QA/Image Forge ni intenta levantar modelos automáticamente. Si una skill no está accesible en el entorno en uso, declarar `CAPABILITY_NOT_AVAILABLE` y ofrecer un plan o conector autorizado.

En Termux se observó que `kai-image-forge-unified` conserva `KAI_FORGE_ZERO_SPEND_MODE=1` para su servicio. Nunca sortear el guard ni interpretar token disponible como consentimiento de gasto. La cooperación entre skills requiere consentimiento de acciones externas y receipts separados.
