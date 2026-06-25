import os

from turing.cli import main as main_module


def test_load_env_sets_missing_keys(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("# comment\nGEMINI_API_KEY=abc123\nEMPTY\n\nFOO = bar \n")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("FOO", raising=False)
    main_module.load_env(env)
    assert os.environ["GEMINI_API_KEY"] == "abc123"
    assert os.environ["FOO"] == "bar"


def test_load_env_does_not_override_existing(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("GEMINI_API_KEY=fromfile")
    monkeypatch.setenv("GEMINI_API_KEY", "fromenv")
    main_module.load_env(env)
    assert os.environ["GEMINI_API_KEY"] == "fromenv"


def test_load_env_missing_file_is_noop(tmp_path):
    main_module.load_env(tmp_path / "nope.env")  # must not raise


def test_parser_parses_source():
    args = main_module.build_parser().parse_args(["source", "--model", "m", "--force"])
    assert args.command == "source"
    assert args.model == "m"
    assert args.force is True


def test_main_dispatches(monkeypatch):
    monkeypatch.setattr(main_module, "load_env", lambda *a, **k: None)
    called = {}
    monkeypatch.setattr(
        main_module.cmd_source, "run", lambda args, **kw: called.setdefault("ran", 0) or 7
    )
    assert main_module.main(["source"]) == 7
    assert "ran" in called


def test_parser_parses_chat_defaults():
    args = main_module.build_parser().parse_args(["chat"])
    assert args.command == "chat"
    assert args.persona == "student"
    assert args.web is False and args.cli is False
    assert args.keep is None


def test_parser_chat_rejects_cli_and_web_together():
    import pytest

    with pytest.raises(SystemExit):
        main_module.build_parser().parse_args(["chat", "--cli", "--web"])
