import os
import tempfile
from typing import Protocol

from google import genai

DEFAULT_MODEL = "gemini-2.5-pro"
TRANSCRIBE_PROMPT = (
    "Transcribe this scanned document to clean GitHub-flavored Markdown. "
    "Preserve the author's exact words, paragraph breaks, and any headings or "
    "lists. Do not summarise, correct, modernise, or add commentary. Mark any "
    "illustrations or diagrams as [diagram]. If a word is illegible, write "
    "[illegible]."
)


class Transcriber(Protocol):
    def transcribe(self, pdf_bytes: bytes) -> str: ...


class FakeTranscriber:
    def __init__(self, text: str) -> None:
        self._text = text
        self.last_pdf_bytes: bytes | None = None

    def transcribe(self, pdf_bytes: bytes) -> str:
        self.last_pdf_bytes = pdf_bytes
        return self._text


class GeminiTranscriber:
    def __init__(self, *, model: str = DEFAULT_MODEL, client=None) -> None:
        self._model = model
        self._client = client or genai.Client()

    def transcribe(self, pdf_bytes: bytes) -> str:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            path = tmp.name
        try:
            uploaded = self._client.files.upload(file=path)
            response = self._client.models.generate_content(
                model=self._model,
                contents=[TRANSCRIBE_PROMPT, uploaded],
            )
            return response.text or ""
        finally:
            os.unlink(path)
