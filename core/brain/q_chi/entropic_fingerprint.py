"""EntropicFingerprintBuilder — cognitive DNA of each decision.

Every significant Q-CHI decision leaves an immutable, hashed trace.
This is explainable traceability, not decorative logging.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime
from typing import Any

from .schemas import CHIState, EntropicFingerprint, Mode, NucleusVote, PituitaryState


class EntropicFingerprintBuilder:
    """Build and sign a fingerprint for each runtime cycle."""

    def build(
        self,
        *,
        chi: CHIState,
        pituitary: PituitaryState,
        nuclei_called: list[str],
        votes: list[NucleusVote],
        final_output: str,
        mode: Mode,
    ) -> EntropicFingerprint:
        chi_dict = asdict(chi)
        pituitary_dict = asdict(pituitary)
        votes_list = [asdict(v) for v in votes]

        payload: dict[str, Any] = {
            "mode": mode,
            "chi": chi_dict,
            "pituitary": pituitary_dict,
            "nuclei_called": nuclei_called,
            "votes": votes_list,
            "final_output": final_output,
        }

        return EntropicFingerprint(
            timestamp=datetime.utcnow().isoformat() + "Z",
            mode=mode,
            chi_state=chi_dict,
            pituitary_state=pituitary_dict,
            nuclei_called=nuclei_called,
            votes=votes_list,
            final_output=final_output,
            hash_value=self.compute_hash(payload),
        )

    def compute_hash(self, payload: dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()
