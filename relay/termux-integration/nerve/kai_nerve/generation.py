from __future__ import annotations
from dataclasses import dataclass
import secrets
@dataclass(frozen=True)
class GenerationToken:
    scope:str;generation:int;nonce:str
class GenerationClock:
    """Reject async results created for an older world/session generation."""
    def __init__(self):self._g={}
    def next(self,scope):
        g=self._g.get(scope,0)+1;self._g[scope]=g;return GenerationToken(scope,g,secrets.token_hex(8))
    def current(self,token):return self._g.get(token.scope,0)==token.generation
