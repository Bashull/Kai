# KAI NERVE Fusion Architecture

Minecraft Bedrock
-> KAI NERVE Sensor + existing visual stream
-> SELECT ONE EXISTING ENGINE TRANSPORT: logcat OR mcwss OR bedrock-ws
-> normalizer/provenance/session/freshness
-> WorldBus SQLite/WAL
-> read-only skills + reflex policy
-> ONE physical control owner
-> calibrated driver

Rules:
- one canonical Bedrock transport owner;
- one physical controller owner;
- vision corroborates but does not fabricate engine truth;
- WorldBus = operational memory, Drive = canon, GitHub = code authority;
- this candidate deliberately binds no new Bedrock port.
