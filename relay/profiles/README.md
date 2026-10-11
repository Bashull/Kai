# Kai runtime profiles

Profiles are shell environment fragments sourced by the runit service.

- `balanced.env`: verified baseline for the S24 Bedrock loop.
- Device-specific hardware belongs in `~/.kai_mobile/hardware.env`, which is not committed.
- The active profile is selected through `~/.kai_mobile/profiles/active.env`.
- Use `relay/kai-profile` to switch profiles with health-check and rollback.

Do not put tokens, ADB pairing data, private server addresses, or credentials in profile files.
