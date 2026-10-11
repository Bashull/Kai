# Skill/Tool/MCP runbook v0.2
**Alcance:** MCP stdio offline. No es un servidor remoto ni un conector instalado en ChatGPT.

Arranque con un cliente compatible y autorizado:
`python -m kai_harvester.mcp_bridge --root "$HOME/KAI_RUNTIME_LAB/chatgpt-harvester"`
Solo stdin/stdout JSON-RPC. No se crean listeners TCP/HTTP, no se exponen cookies ni tokens.
Herramientas: doctor/stats/audit/asset_gaps/search. Nunca crea ni elimina mensajes en ChatGPT.
Usar siempre primero doctor + audit y comprobar scope del corpus. El resultado de search solo representa material importado, incluyendo ramas presentes en RAW.
Errores: SQL FTS ausente -> búsqueda lineal; grafo parcial -> no certificar completitud; falta de permiso externo -> blocked; JSON malformado -> respuesta de error sin dump de secretos.
No ejecutar este puente en un directorio con conversaciones sensibles en un host MCP desconocido; los resultados devuelven fragmentos explícitos al cliente autorizado.
