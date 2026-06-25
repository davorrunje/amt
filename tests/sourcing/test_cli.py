from pathlib import Path

from typer.testing import CliRunner

from turing.sourcing import __main__ as cli
from turing.sourcing.browser import FakeBrowser
from turing.sourcing.models import FetchResult
from turing.sourcing.transcriber import FakeTranscriber

FIXTURE = (Path(__file__).parent / "fixtures" / "item_synthetic.html").read_text()


def _sources_file(tmp_path):
    p = tmp_path / "sources.yaml"
    p.write_text("sources:\n  - ref: AMT/C/10\n    title: T\n    type: ms\n")
    return p


def test_run_sourcing_with_injected_fakes(tmp_path, capsys):
    sources = _sources_file(tmp_path)
    browser = FakeBrowser(FetchResult(html=FIXTURE, pdf_url="https://x/s.pdf", pdf_bytes=b"%PDF"))
    code = cli.run_sourcing(
        sources=str(sources),
        corpus_dir=str(tmp_path / "c"),
        cache_dir=str(tmp_path / "cache"),
        browser=browser,
        transcriber=FakeTranscriber("BODY"),
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "AMT/C/10" in out and "written" in out
    assert (tmp_path / "c" / "amt-c-10.md").exists()


def test_run_sourcing_nonzero_on_error(tmp_path):
    sources = _sources_file(tmp_path)

    class _Boom:
        def fetch(self, url):
            raise RuntimeError("boom")

    code = cli.run_sourcing(
        sources=str(sources),
        corpus_dir=str(tmp_path / "c"),
        cache_dir=str(tmp_path / "cache"),
        browser=_Boom(),
        transcriber=FakeTranscriber("B"),
    )
    assert code == 1


def test_run_sourcing_builds_default_adapters(tmp_path, monkeypatch):
    sources = _sources_file(tmp_path)
    built = {}
    monkeypatch.setattr(cli, "PlaywrightBrowser", lambda **kw: built.setdefault("b", object()))
    monkeypatch.setattr(cli, "GeminiTranscriber", lambda **kw: built.setdefault("t", object()))
    monkeypatch.setattr(cli, "run", lambda *a, **kw: [])
    code = cli.run_sourcing(
        sources=str(sources),
        corpus_dir=str(tmp_path / "c"),
        cache_dir=str(tmp_path / "cache"),
    )
    assert code == 0
    assert "b" in built and "t" in built


def test_cli_app_invokes_run_sourcing(monkeypatch):
    captured = {}
    monkeypatch.setattr(cli, "run_sourcing", lambda **kw: captured.update(kw) or 0)
    result = CliRunner().invoke(cli.app, ["--model", "gemini-2.5-flash", "--force"])
    assert result.exit_code == 0
    assert captured["model"] == "gemini-2.5-flash"
    assert captured["force"] is True


def test_cli_app_propagates_nonzero(monkeypatch):
    monkeypatch.setattr(cli, "run_sourcing", lambda **kw: 1)
    result = CliRunner().invoke(cli.app, [])
    assert result.exit_code == 1


def test_main_invokes_app(monkeypatch):
    called = {}
    monkeypatch.setattr(cli, "app", lambda: called.setdefault("ran", True))
    cli.main()
    assert called["ran"] is True
