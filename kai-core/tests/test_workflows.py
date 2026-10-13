from kai_core.workflows.extract_document import process_document
from kai_core.workflows.compare_alma_kai import compare_alma_kai


class FakeConnector:
    def readFileText(self, fileId: str):
        return {"text": f"{fileId} debe mantener identidad y memoria con backup obligatorio."}


def test_process_document_outputs_gate():
    out = process_document("docA", "masterA", connector=FakeConnector())
    assert out["ready_to_move_complete"] is False
    assert "extraction" in out


def test_compare_alma_kai_outputs_target_master():
    out = compare_alma_kai("alma_de_kai", "alma_kai", connector=FakeConnector())
    assert out["target_master"] == "KAI_IDENTIDAD_ALMA_ORIGENES_MAESTRO"
    assert out["can_move_originals_to_complete"] is False
