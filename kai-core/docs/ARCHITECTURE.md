# KAI CORE Architecture

KAI CORE se organiza en capas:

1. **Connectors**: acceso seguro a Drive, Docs, Apps Script y GitHub.
2. **Ingestion**: lectura e inventario de documentos/repositorios.
3. **Extraction**: resumen, canon candidato, directivas y contradicciones.
4. **Memory**: episódica, semántica, canónica y operativa con persistencia.
5. **Workflows**: procesos supervisados para extracción, comparación y auditoría.
6. **Agents**: Supervisor, Archivist, Extractor, Unifier, Coder, Researcher, Auditor, ChiQGuardian.
7. **CLI**: interfaz operativa para ejecutar flujos auditables.

Toda operación sensible pasa por validación de seguridad y registro de auditoría.
