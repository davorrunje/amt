import os

import pytest

pytestmark = pytest.mark.live


@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
def test_live_fetch_and_transcribe(tmp_path):
    from turing.sourcing.browser import PlaywrightBrowser
    from turing.sourcing.models import SourceEntry
    from turing.sourcing.pipeline import run
    from turing.sourcing.transcriber import GeminiTranscriber

    results = run(
        [SourceEntry(ref="AMT/C/10", title="Morphogenesis", type="ms")],
        browser=PlaywrightBrowser(delay=0),
        transcriber=GeminiTranscriber(),
        corpus_dir=tmp_path / "corpus",
        cache_dir=tmp_path / "cache",
    )
    assert results[0].status == "written"
    assert (tmp_path / "corpus" / "amt-c-10.md").read_text().strip()
