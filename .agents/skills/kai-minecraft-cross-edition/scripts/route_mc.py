"""Read-only edition router. It never connects to a game or performs actions."""
import argparse
import json

EDITIONS = {'java', 'bedrock', 'crossplay', 'unknown'}
SERVERS = {'paper', 'spigot', 'fabric', 'forge', 'bedrock-dedicated',
           'powernukkitx', 'geyser-java', 'unknown'}
INTENTS = {'observe', 'chat', 'move', 'build', 'voice', 'npc'}
JAVA = {'paper', 'spigot', 'fabric', 'forge'}
BEDROCK = {'bedrock-dedicated', 'powernukkitx'}


def plan(edition: str, server: str, intent: str) -> dict:
    """Return a conservative architecture plan, not permission to execute."""
    if edition not in EDITIONS or server not in SERVERS or intent not in INTENTS:
        raise ValueError('Unsupported edition, server software or intent')
    if (edition == 'java' and server in BEDROCK) or (edition == 'bedrock' and server in JAVA | {'geyser-java'}):
        raise ValueError('Edition does not match server software')
    if edition == 'crossplay' and server not in {'geyser-java', 'unknown'}:
        raise ValueError('Crossplay must be verified as Java-hosted Geyser')

    result = {
        'edition': edition, 'server_software': server, 'intent': intent,
        'adapter': 'none', 'authorization': 'required_before_live_actions',
        'dry_run_only': True, 'deployed': False, 'needs_server_test': True,
        'geyser_translation': False, 'warning': '',
        'next_step': 'identify_server_edition_software_version',
    }
    if server == 'unknown' or edition == 'unknown':
        return result
    if edition == 'java' and server in JAVA:
        result.update(adapter='mineflayer_mcp',
                      warning='Java client only; RCON is separate from game connection',
                      next_step='verify_version_auth_permissions_on_private_test_server')
    elif edition == 'bedrock' and server in BEDROCK:
        result.update(adapter='bedrock_protocol_candidate',
                      warning='Low-level protocol requires server acknowledgement and compatible auth',
                      next_step='probe_bedrock_version_auth_in_isolated_world')
    elif edition == 'crossplay' and server == 'geyser-java':
        result.update(adapter='mineflayer_mcp', geyser_translation=True,
                      warning='Geyser bridges Bedrock players into Java; not a native Bedrock bot',
                      next_step='verify_geyser_floodgate_and_java_server_versions')
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Edition-aware, read-only Codex planning')
    parser.add_argument('--edition', choices=sorted(EDITIONS), required=True)
    parser.add_argument('--server', choices=sorted(SERVERS), required=True)
    parser.add_argument('--intent', choices=sorted(INTENTS), required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(plan(args.edition, args.server, args.intent), indent=2, ensure_ascii=False))
    except ValueError as exc:
        parser.error(str(exc))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
