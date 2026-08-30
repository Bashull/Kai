from __future__ import annotations

from dataclasses import asdict
from typing import Any

from kai_core.connectors.google_drive import GoogleDriveConnector
from kai_core.extraction.document_extractor import extract_document

TARGET_MASTER = "KAI_IDENTIDAD_ALMA_ORIGENES_MAESTRO"


def compare_alma_kai(file_id_a: str, file_id_b: str, connector: GoogleDriveConnector | None = None) -> dict[str, Any]:
    connector = connector or GoogleDriveConnector()

    a_raw = connector.readFileText(file_id_a)
    b_raw = connector.readFileText(file_id_b)

    a_text = a_raw.get("text") or a_raw.get("content") or ""
    b_text = b_raw.get("text") or b_raw.get("content") or ""

    a_ext = extract_document(a_text, related_docs=[b_text])
    b_ext = extract_document(b_text, related_docs=[a_text])

    a_set = set([x.lower() for x in a_ext.useful_ideas])
    b_set = set([x.lower() for x in b_ext.useful_ideas])

    return {
        "documents": {
            "alma_de_kai": {"file_id": file_id_a, "extraction": asdict(a_ext)},
            "alma_kai": {"file_id": file_id_b, "extraction": asdict(b_ext)},
        },
        "comparison": {
            "shared_ideas": sorted(a_set.intersection(b_set))[:20],
            "unique_alma_de_kai": sorted(a_set.difference(b_set))[:20],
            "unique_alma_kai": sorted(b_set.difference(a_set))[:20],
            "potential_contradictions": sorted(set(a_ext.contradictions + b_ext.contradictions))[:20],
            "recommended_unification_actions": [
                "actualizar_bloque_identidad_en_maestro",
                "insertar_notas_cruzadas_origenes",
                "registrar_decisiones_canonicas",
            ],
        },
        "target_master": TARGET_MASTER,
        "can_move_originals_to_complete": False,
        "gate": "Solo tras actualización del maestro y registro de integración/auditoría",
    }
