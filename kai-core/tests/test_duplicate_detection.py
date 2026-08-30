from kai_core.extraction.duplicate_detector import find_related_duplicates


def test_find_related_duplicates_detects_overlap():
    text = "alma identidad origen memoria coherencia"
    related = [
        "alma identidad origen con nuevas notas",
        "tema de infraestructura terraform cloud",
    ]
    result = find_related_duplicates(text, related)
    assert len(result) == 1
