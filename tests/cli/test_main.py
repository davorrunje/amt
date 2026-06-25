import os

from typer.testing import CliRunner

from turing.cli import main as main_module

runner = CliRunner()


def test_load_env_sets_missing_keys(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("# comment\nGEMINI_API_KEY=abc123\nEMPTY\n\nFOO = bar \n")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("FOO", raising=False)
    main_module.load_env(env)
    assert os.environ["GEMINI_API_KEY"] == "abc123"
    assert os.environ["FOO"] == "bar"
    assert "EMPTY" not in os.environ


def test_load_env_does_not_override_existing(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("GEMINI_API_KEY=fromfile")
    monkeypatch.setenv("GEMINI_API_KEY", "fromenv")
    main_module.load_env(env)
    assert os.environ["GEMINI_API_KEY"] == "fromenv"


def test_load_env_missing_file_is_noop(tmp_path):
    main_module.load_env(tmp_path / "nope.env")


def test_source_command_wires_args(monkeypatch):
    monkeypatch.setattr(main_module, "load_env", lambda *a, **k: None)
    captured = {}
    monkeypatch.setattr(main_module.cmd_source, "run", lambda **kw: captured.update(kw) or 0)
    result = runner.invoke(main_module.app, ["source", "--model", "m", "--force"])
    assert result.exit_code == 0
    assert captured == {"model": "m", "force": True}


def test_chat_command_wires_args(monkeypatch):
    monkeypatch.setattr(main_module, "load_env", lambda *a, **k: None)
    captured = {}
    monkeypatch.setattr(main_module.cmd_chat, "run", lambda **kw: captured.update(kw) or 0)
    result = runner.invoke(main_module.app, ["chat", "--web", "--persona", "colleague"])
    assert result.exit_code == 0
    assert captured == {"web": True, "persona": "colleague", "keep": None}


def test_chat_defaults_to_student_terminal(monkeypatch):
    monkeypatch.setattr(main_module, "load_env", lambda *a, **k: None)
    captured = {}
    monkeypatch.setattr(main_module.cmd_chat, "run", lambda **kw: captured.update(kw) or 0)
    result = runner.invoke(main_module.app, ["chat"])
    assert result.exit_code == 0
    assert captured == {"web": False, "persona": "student", "keep": None}


def test_chat_rejects_unknown_persona(monkeypatch):
    monkeypatch.setattr(main_module, "load_env", lambda *a, **k: None)
    result = runner.invoke(main_module.app, ["chat", "--persona", "bogus"])
    assert result.exit_code != 0


def test_personas_command_wires_args(monkeypatch):
    monkeypatch.setattr(main_module, "load_env", lambda *a, **k: None)
    captured = {}
    monkeypatch.setattr(main_module.cmd_personas, "run", lambda **kw: captured.update(kw) or 0)
    result = runner.invoke(main_module.app, ["personas", "--prompt", "x", "--apply"])
    assert result.exit_code == 0
    assert captured == {"prompt": "x", "apply": True}


def test_command_propagates_nonzero(monkeypatch):
    monkeypatch.setattr(main_module, "load_env", lambda *a, **k: None)
    monkeypatch.setattr(main_module.cmd_source, "run", lambda **kw: 3)
    result = runner.invoke(main_module.app, ["source"])
    assert result.exit_code == 3


def test_main_invokes_app(monkeypatch):
    called = {}
    monkeypatch.setattr(main_module, "app", lambda: called.setdefault("ran", True))
    main_module.main()
    assert called["ran"] is True
