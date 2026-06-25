from pathlib import Path

from turing.sourcing.browser import FakeBrowser
from turing.sourcing.models import FetchResult, SourceEntry
from turing.sourcing.pipeline import load_sources, run
from turing.sourcing.transcriber import FakeTranscriber

FIXTURE = (Path(__file__).parent / "fixtures" / "item_synthetic.html").read_text()


def test_load_sources(tmp_path):
    p = tmp_path / "sources.yaml"
    p.write_text("sources:\n  - ref: AMT/C/10\n    title: T\n    type: ms\n")
    entries = load_sources(p)
    assert entries == [SourceEntry(ref="AMT/C/10", title="T", type="ms")]


def _browser(pdf=b"%PDF"):
    return FakeBrowser(FetchResult(html=FIXTURE, pdf_url="https://x/scan.pdf", pdf_bytes=pdf))


def test_run_writes_item_and_caches_pdf(tmp_path):
    corpus_dir = tmp_path / "corpus"
    cache_dir = tmp_path / "cache"
    results = run(
        [SourceEntry(ref="AMT/C/10", title="Morpho", type="ms")],
        browser=_browser(b"%PDF-bytes"),
        transcriber=FakeTranscriber("BODY"),
        corpus_dir=corpus_dir,
        cache_dir=cache_dir,
    )
    assert results[0].status == "written"
    assert (corpus_dir / "amt-c-10.md").exists()
    assert (cache_dir / "amt-c-10.pdf").read_bytes() == b"%PDF-bytes"
    assert "BODY" in (corpus_dir / "amt-c-10.md").read_text()


def test_run_skips_when_done(tmp_path):
    corpus_dir = tmp_path / "corpus"
    cache_dir = tmp_path / "cache"
    browser = _browser()
    transcriber = FakeTranscriber("B")
    run(
        [SourceEntry(ref="AMT/C/10")],
        browser=browser,
        transcriber=transcriber,
        corpus_dir=corpus_dir,
        cache_dir=cache_dir,
    )
    results = run(
        [SourceEntry(ref="AMT/C/10")],
        browser=browser,
        transcriber=transcriber,
        corpus_dir=corpus_dir,
        cache_dir=cache_dir,
    )
    assert results[0].status == "skipped"


def test_run_force_reprocesses(tmp_path):
    corpus_dir = tmp_path / "corpus"
    cache_dir = tmp_path / "cache"
    browser = _browser()
    transcriber = FakeTranscriber("B")
    run(
        [SourceEntry(ref="AMT/C/10")],
        browser=browser,
        transcriber=transcriber,
        corpus_dir=corpus_dir,
        cache_dir=cache_dir,
    )
    results = run(
        [SourceEntry(ref="AMT/C/10")],
        force=True,
        browser=browser,
        transcriber=transcriber,
        corpus_dir=corpus_dir,
        cache_dir=cache_dir,
    )
    assert results[0].status == "written"


def test_run_no_pdf(tmp_path):
    browser = FakeBrowser(FetchResult(html=FIXTURE, pdf_url=None, pdf_bytes=None))
    results = run(
        [SourceEntry(ref="AMT/C/10")],
        browser=browser,
        transcriber=FakeTranscriber("B"),
        corpus_dir=tmp_path / "c",
        cache_dir=tmp_path / "cache",
    )
    assert results[0].status == "no_pdf"


def test_run_captures_errors(tmp_path):
    class _Boom:
        def fetch(self, url):
            raise RuntimeError("network down")

    results = run(
        [SourceEntry(ref="AMT/C/10")],
        browser=_Boom(),
        transcriber=FakeTranscriber("B"),
        corpus_dir=tmp_path / "c",
        cache_dir=tmp_path / "cache",
    )
    assert results[0].status == "error"
    assert results[0].error is not None
    assert "network down" in results[0].error
