# KAI CORE

Sistema operativo agente persistente para extracción documental, memoria operativa y control CHI-Q.

## Instalación

```bash
cd kai-core
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Comandos CLI

```bash
kai scan-drive
kai read-doc FILE_ID
kai extract-doc FILE_ID
kai compare FILE_ID_A FILE_ID_B
kai unify-topic identidad
kai research-github "agent memory"
kai chiq
kai audit
```

## Seguridad operativa

- Nunca almacenar secretos en código.
- Toda escritura documental exige backup + aprobación + hash esperado.
- Auditoría local en `logs/audit.jsonl`.

## Plan de despliegue

Ver `docs/DEPLOYMENT_PLAN.md`.
