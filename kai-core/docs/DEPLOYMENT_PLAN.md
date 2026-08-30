# DEPLOYMENT PLAN

1. Configurar variables de entorno y credenciales fuera del repositorio.
2. Desplegar servicio CLI/API en contenedor aislado.
3. Configurar almacenamiento persistente para `logs/` y memoria.
4. Integrar secreto de GitHub token y endpoint de Apps Script por entorno.
5. Activar ejecución programada de `daily_audit`.
6. Definir circuito de aprobación humana para cambios de escritura.
