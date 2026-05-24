# SECURITY

Principios obligatorios:

- No exponer secretos ni imprimir tokens.
- No escritura sin hash previo (`expectedSha256`).
- No escritura sin `createBackup=true` y `asierApproved=true`.
- Operaciones administrativas requieren `adminApproved=true`.
- No borrado definitivo: solo movimiento controlado.
- Auditoría completa de cambios en `logs/audit.jsonl`.
