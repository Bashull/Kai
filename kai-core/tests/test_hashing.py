from kai_core.tools.hashing import sha256_text


def test_sha256_text_is_deterministic():
    assert sha256_text("kai") == sha256_text("kai")
    assert len(sha256_text("kai")) == 64
