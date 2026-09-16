# KAI Nervous Link Android / MobileNode — Runtime Status

**As of:** 2026-09-16  
**Scope:** runtime evidence only; source preservation is still pending.

## Verified runtime state

- Installed Android package: `com.kai.mobilenode`.
- Installed version: `0.5.1` (`versionCode 7`).
- The local working source observed during repair lives at `C:\Kai\MobileNode` on the Windows node.
- Runtime Relay endpoint override is loaded from app-private storage, with the compiled endpoint retained only as fallback.
- The endpoint can therefore change without rebuilding the APK.
- Unit tests for endpoint resolution passed before the APK was built and installed.
- A complete debug unit-test + debug APK build passed before installation.
- Relay heartbeat from device `mobile-ui-s24` was restored through HTTPS transport.
- Accessibility service state was effect-verified through an end-to-end `UI_COMMAND screen_state` result.
- The Relay result reached `COMPLETED / SUCCEEDED` and reported `serviceActive=true`.

## Security boundary retained

This runtime repair did **not** add an unrestricted exported broadcast receiver or a generic remote shell surface. Runtime endpoint configuration is private to the app sandbox. Raw private UI-tree content must not be persisted into GitHub or normal project documentation.

The normative Android requirements remain in `CONTRACT.md`.

## Source authority gap

The branch currently contains only the Android contract and this status record. The MobileNode Android project source has **not yet been preserved in GitHub**. Do not infer source authority from the installed APK or this document.

The first source-preservation operation must recover the exact current `C:\Kai\MobileNode` project, compare it against the Android contract, exclude local secrets/generated build outputs, preserve tests and build configuration, and then commit it under a deliberate canonical Android source path.

## Transport state

- Current public Relay path has been proven through an ephemeral Cloudflare Quick Tunnel.
- That Quick Tunnel is not durable authority because its hostname changes.
- Approved transport direction remains: Cloudflare Tunnel primary, Tailscale Personal fallback.
- Tailscale is installed on Windows and Android; Windows login authorization was completed by Asier, but post-login peer/Serve verification remains pending.
- `HOME_LAN_INDEPENDENT` must not be claimed until the S24 succeeds over mobile data with home Wi-Fi disabled.

## Next verification gates

1. Re-establish command authority over the Windows node.
2. Verify Windows Tailscale authenticated state and S24 membership in the same tailnet.
3. Publish local Relay `127.0.0.1:8788` privately with Tailscale Serve and verify its stable tailnet HTTPS endpoint.
4. Point MobileNode 0.5.1 at that stable private endpoint through its app-private runtime configuration.
5. Verify fresh heartbeat and `UI_COMMAND screen_state` while still on home Wi-Fi.
6. Disable S24 Wi-Fi, leave mobile data enabled, and repeat the same end-to-end test.
7. Only after effect proof may the state be recorded as `REMOTE_MOBILE_CONTROL · HOME_LAN_INDEPENDENT · VERIFIED`.
8. Recover and preserve the exact MobileNode 0.5.1 source tree in GitHub, then record the resulting commit SHA in CURRENT authorities.
