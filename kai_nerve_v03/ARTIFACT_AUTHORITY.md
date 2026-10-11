# KAI NERVE Termux + GPT v0.3 CANDIDATE

Status: **CANDIDATE / NOT DEPLOYED / NOT ARMED**

This branch records the v0.3 fusion checkpoint produced from the Drive donor corpus on 2026-10-11.

## Exact artifact

- `KAI_NERVE_Termux_GPT_v0.3_CANDIDATE.zip`
- SHA-256: `4477970b5c1e3423c59246ef3fa4aa8c4cd605210551da85ad73d5c67ca7fe6a`
- Sensor mcpack SHA-256: `e649635e081f93de53191d4eaf00cd6e7f3693d5ccd83a7310c60b3aaa699487`
- Source Drive folder ID: `1S80uw_ACHy9J6qNXMIN9ngZ-fkQWh3s8`

The exact candidate ZIP is stored in the source Drive folder. This branch does **not** yet claim that every source file of the ZIP has been promoted to GitHub; until that promotion, the ZIP hash above is the byte-level authority for v0.3.

## Validation

- 27/27 top-level ZIP donors opened successfully.
- 7 nested ZIP/JAR containers were enumerated without executing donor code.
- 17,298 outer+nested file records inventoried.
- 26/26 v0.3 unit tests passed in the build environment.
- Sensor JavaScript syntax check passed.
- Sensor mcpack ZIP integrity passed.

## Safety / truth state

Not demonstrated yet:
- authentic Bedrock → Termux → existing WorldBus event;
- sustained runtime reliability;
- safe physical control;
- autonomous survival.

First controlled milestone:
Bedrock sensor in a copied/test world → PID-filtered logcat collector → collector-owned provenance/challenge → freshness/replay checks → exact same event persisted and read back from existing WorldBus.

Do not restart bridges by intuition. Do not arm physical actuation. Do not use the canonical world for the first sensor E2E test.
