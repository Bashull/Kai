# KAI Nervous Link Android Client Contract

Android/MobileNode must send only typed protocol envelopes from `protocol/envelope.js`.

It must not expose an unrestricted exported broadcast receiver that accepts arbitrary shell text.

Required client responsibilities:

- hold only revocable client credentials;
- require explicit Asier approval for pairing;
- show connected device identity and last heartbeat;
- support typed actions only;
- display audit ID for every response;
- expose a local emergency disconnect action;
- never log raw long-lived credentials;
- preserve Android sandbox boundaries.

The first Android integration target is Kai MobileNode. The v0.1 relay/agent must remain usable without modifying MobileNode.

Future MobileNode integration should prefer an explicit internal service or authenticated bound interface over generic exported broadcasts. Commands must map to protocol actions and capabilities, not arbitrary shell strings.
