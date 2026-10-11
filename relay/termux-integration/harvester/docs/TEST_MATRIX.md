# Verification matrix

## Tests actually run on the delivered source

- Python `unittest` on synthetic graphs and ZIPs: branch sibling recovery, active path, text literal preservation, orphan/cycle/current node detection, idempotency, raw revision isolation, manifest, reader, evidence corruption, input size guard, unsafe ZIP member, asset refs vs physical, KAI bridge envelope.
- `node --check extension/bridge.js`: JavaScript syntax only.
- Python `compileall`: syntax only.

## Not tested / unsafe to claim

- Live ChatGPT session, login, account and workspace permission matrix.
- Real 429 Retry-After behavior, 404 endpoint drift, valid Projects cursor exhaust, archived coverage.
- Huge real exports 10 GiB, actual Termux runtime on user's Samsung device, mobile browser loading unpacked extensions.
- Binary Project asset resolver and signed URL lifetime.
- Temporary Chats and all branches of regenerated replies under latest paginated messages.
- Runtime health of the original Devourer and connected PC/Termux.

## Promotion gates

1. Run synthetic tests in Termux and desktop, capture OS/Python/Node versions.
2. Threat-model permissions, network paths, storage and sensitive file-handling.
3. User-approved sandbox ChatGPT account for browser testing, current endpoints and B2B workspace probes.
4. Fixture-verified counters for requested main/archived/projects/shared scopes, pagination and no false COMPLETE.
5. Asset count, hash, routing and physical byte recovery; DAG branch parity against independent RAW official source.
6. Reconciliation with canonical Devourer CURRENT, project checkpoint/wiki and rollback plan.
7. Only then consider PROMOTED; never infer CANONICAL from tests alone.
