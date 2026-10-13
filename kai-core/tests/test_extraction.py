from kai_core.extraction.document_extractor import extract_document


def test_extract_document_returns_structured_fields():
    text = "Kai debe preservar memoria. Nunca borrar sin backup. CHI mejora coherencia."
    result = extract_document(text)
    assert result.summary_short
    assert "identidad" in result.affected_themes or result.affected_themes
    assert isinstance(result.canonical_candidates, list)
