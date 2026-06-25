from types import SimpleNamespace

from turing.cli import cmd_source


def test_run_delegates_and_passes_model_force(monkeypatch):
    captured = {}

    def fake_run_sourcing(**kw):
        captured.update(kw)
        return 0

    monkeypatch.setattr(cmd_source, "run_sourcing", fake_run_sourcing)
    code = cmd_source.run(
        SimpleNamespace(model="gemini-2.5-flash", force=True),
        browser=object(),
        transcriber=object(),
    )
    assert code == 0
    assert captured["model"] == "gemini-2.5-flash"
    assert captured["force"] is True


def test_run_prints_chromium_hint_on_failure(monkeypatch, capsys):
    monkeypatch.setattr(cmd_source, "run_sourcing", lambda **kw: 1)
    code = cmd_source.run(
        SimpleNamespace(model="m", force=False),
        browser=object(),
        transcriber=object(),
    )
    assert code == 1
    assert "playwright install chromium" in capsys.readouterr().err
