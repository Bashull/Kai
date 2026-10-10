#!/usr/bin/env python3
"""Offline, deterministic event-to-commentary bridge. No network or game access.

The caller must authenticate and authorize the event source before invoking this
object: a caller-supplied `trusted` field is never proof of origin. This module
only validates the shape and sequence of mock/event records.
"""
import re

IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
PLAYER = re.compile(r"^[A-Za-z0-9_]{1,24}$")


class EventBridge:
    def __init__(self):
        self.matches = {}
        self.seen = set()

    @staticmethod
    def _reject(reason):
        return {"status": "rejected", "reason": reason}

    def process(self, event):
        if not isinstance(event, dict):
            return self._reject("invalid_event")
        ident, match_id = event.get("id"), event.get("match_id")
        if (not isinstance(ident, str) or not IDENTIFIER.fullmatch(ident)
                or not isinstance(match_id, str) or not IDENTIFIER.fullmatch(match_id)):
            return self._reject("invalid_identifier")
        if event.get("trusted") is False:
            return self._reject("untrusted_source")
        if ident in self.seen:
            return self._reject("duplicate_event")
        kind = event.get("type")
        a, other = event.get("a"), event.get("b")
        if kind not in {"start", "hit", "win"}:
            return self._reject("invalid_type")
        if not isinstance(a, str) or not PLAYER.fullmatch(a):
            return self._reject("invalid_player")
        if kind == "start":
            if not isinstance(other, str) or not PLAYER.fullmatch(other) or a == other:
                return self._reject("invalid_players")
            if match_id in self.matches:
                return self._reject("match_exists")
            self.matches[match_id] = {"players": (a, other), "closed": False}
            text = f"¡Arranca el combate! {a} contra {other}: ¡aquí manda el chuletón!"
        else:
            match = self.matches.get(match_id)
            if match is None:
                return self._reject("match_not_started")
            if match["closed"]:
                return self._reject("match_already_finished")
            if a not in match["players"]:
                return self._reject("player_not_in_match")
            if kind == "win":
                text = f"¡Victoria para {a}! ¡El coliseo de Sóloland está que arde!"
                match["closed"] = True
            else:
                text = f"¡Tremendo chuletazo de {a}! ¡Eso se ha oído hasta en el Nether!"
        self.seen.add(ident)
        return {"status": "accepted", "match_id": match_id, "event_id": ident,
                "spoken_text": text}
