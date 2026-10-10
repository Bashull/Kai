#!/usr/bin/env python3
"""Offline deterministic Sololand fight-call samples (no live event listener)."""
import argparse
import json

EVENTS = {
    'start': '¡Arranca el combate! {a} contra {b}: ¡aquí manda el chuletón!',
    'hit': '¡Tremendo chuletazo de {a}! ¡Eso se ha oído hasta en el Nether!',
    'win': '¡Victoria para {a}! ¡El coliseo de Sóloland está que arde!',
}


def call(event, player_a, player_b='Rival'):
    if event not in EVENTS:
        raise ValueError('Unknown event')
    for name in (player_a, player_b):
        if not (1 <= len(name) <= 24 and name.replace('_', '').isalnum()):
            raise ValueError('Invalid Minecraft player name')
    return EVENTS[event].format(a=player_a, b=player_b)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('event', choices=EVENTS)
    p.add_argument('player_a')
    p.add_argument('player_b', nargs='?', default='Rival')
    args = p.parse_args()
    print(json.dumps({'status': 'offline_demo', 'spoken_text': call(args.event, args.player_a, args.player_b)}, ensure_ascii=False))
