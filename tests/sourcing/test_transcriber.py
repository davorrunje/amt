from types import SimpleNamespace

from turing.sourcing import transcriber as transcriber_module
from turing.sourcing.transcriber import FakeTranscriber, GeminiTranscriber


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
