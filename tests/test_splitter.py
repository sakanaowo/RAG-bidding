from app.data.ingest_utils import text_splitter


def test_text_split():
    text = "Hello\n" * 100
    parts = text_splitter.split_text(text)
    assert len(parts) > 1
