from types import SimpleNamespace

from turing.cli import cmd_source


def test_run_delegates_and_passes_model_force(monkeypatch):
    captured = {}

    def fake_sourcing_main(argv, *, browser=None, transcriber=None):
        captured["argv"] = argv
        return 0

    monkeypatch.setattr(cmd_source, "sourcing_main", fake_sourcing_main)
    code = cmd_source.run(
        SimpleNamespace(model="gemini-2.5-flash", force=True),
        browser=object(),
        transcriber=object(),
    )
    assert code == 0
    assert captured["argv"] == ["--model", "gemini-2.5-flash", "--force"]


def test_run_prints_chromium_hint_on_failure(monkeypatch, capsys):
    monkeypatch.setattr(cmd_source, "sourcing_main", lambda argv, **kw: 1)
    code = cmd_source.run(
        SimpleNamespace(model="m", force=False),
        browser=object(),
        transcriber=object(),
    )
    assert code == 1
    assert "playwright install chromium" in capsys.readouterr().err
