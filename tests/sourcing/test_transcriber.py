import io
from types import SimpleNamespace

from pypdf import PdfReader, PdfWriter

from turing.sourcing import transcriber as transcriber_module
from turing.sourcing.transcriber import FakeTranscriber, GeminiTranscriber, _split_pdf


def _make_pdf(n_pages: int) -> bytes:
    writer = PdfWriter()
    for _ in range(n_pages):
        writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_faketranscriber_returns_text_and_records_bytes():
    fake = FakeTranscriber("transcribed text")
    assert fake.transcribe(b"%PDF") == "transcribed text"
    assert fake.last_pdf_bytes == b"%PDF"


def test_geminitranscriber_uploads_and_generates(monkeypatch):
    calls = {}

    class _Files:
        def upload(self, *, file):
            calls["uploaded_path"] = file
            return SimpleNamespace(name="files/abc")

    class _Models:
        def generate_content(self, *, model, contents):
            calls["model"] = model
            calls["contents"] = contents
            return SimpleNamespace(text="# Transcription\n\nHello.")

    fake_client = SimpleNamespace(files=_Files(), models=_Models())
    monkeypatch.setattr(transcriber_module.genai, "Client", lambda: fake_client)

    out = GeminiTranscriber().transcribe(b"%PDF-data")
    assert out == "# Transcription\n\nHello."
    assert calls["model"] == "gemini-2.5-pro"
    # the uploaded path is a real temp file that contained the bytes
    assert calls["uploaded_path"].endswith(".pdf")
    # prompt is the first content item, uploaded file the second
    assert calls["contents"][0] == transcriber_module.TRANSCRIBE_PROMPT
    assert calls["contents"][1].name == "files/abc"


def test_geminitranscriber_handles_empty_text(monkeypatch):
    class _Files:
        def upload(self, *, file):
            return SimpleNamespace(name="files/x")

    class _Models:
        def generate_content(self, *, model, contents):
            return SimpleNamespace(text=None)

    fake_client = SimpleNamespace(files=_Files(), models=_Models())
    out = GeminiTranscriber(client=fake_client).transcribe(b"%PDF")
    assert out == ""


def test_split_pdf_returns_single_chunk_when_under_limit():
    data = b"%PDF-small-document"
    assert _split_pdf(data, 1_000_000) == [data]


def test_split_pdf_splits_large_pdf_preserving_all_pages():
    pdf = _make_pdf(6)
    # max_chunk_bytes=1 forces the smallest possible chunks (1 page each).
    chunks = _split_pdf(pdf, max_chunk_bytes=1)
    assert len(chunks) > 1
    total_pages = sum(len(PdfReader(io.BytesIO(c)).pages) for c in chunks)
    assert total_pages == 6


def test_geminitranscriber_concatenates_chunk_transcriptions():
    counter = {"n": 0}

    class _Files:
        def upload(self, *, file):
            return SimpleNamespace(name="files/x")

    class _Models:
        def generate_content(self, *, model, contents):
            counter["n"] += 1
            return SimpleNamespace(text=f"chunk{counter['n']}")

    fake_client = SimpleNamespace(files=_Files(), models=_Models())
    pdf = _make_pdf(4)
    out = GeminiTranscriber(client=fake_client, max_chunk_bytes=1).transcribe(pdf)
    assert counter["n"] == 4  # one Gemini call per page-sized chunk
    assert out == "chunk1\n\nchunk2\n\nchunk3\n\nchunk4"
