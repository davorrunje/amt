import io
from pathlib import Path

from turing.cli import cmd_chat
from turing.core.provider import FakeProvider


def test_run_cli_streams_and_writes_transcript(tmp_path):
    out = io.StringIO()
    keep = tmp_path / "t.md"
    provider = FakeProvider(["Hello", " there"])
    code = cmd_chat.run_cli(
        "student",
        str(keep),
        provider=provider,
        input_stream=iter(["What is mind?", "/quit"]),
        output_stream=out,
    )
    assert code == 0
    assert "Hello there" in out.getvalue()
    transcript = keep.read_text()
    assert "student" in transcript
    assert "What is mind?" in transcript
    assert "Hello there" in transcript
    assert "**You:** What is mind?" in transcript
    assert "**Turing:** Hello there" in transcript


def test_run_cli_stops_on_empty_line(tmp_path):
    keep = tmp_path / "t.md"
    cmd_chat.run_cli(
        "public",
        str(keep),
        provider=FakeProvider(["x"]),
        input_stream=iter([""]),
        output_stream=io.StringIO(),
    )
    # no turns recorded beyond the header
    assert "**You:**" not in keep.read_text()


def test_run_cli_stops_on_quit(tmp_path):
    keep = tmp_path / "t.md"
    cmd_chat.run_cli(
        "public",
        str(keep),
        provider=FakeProvider(["x"]),
        input_stream=iter(["/quit"]),
        output_stream=io.StringIO(),
    )
    # no turns recorded beyond the header
    assert "**You:**" not in keep.read_text()


def test_run_cli_stops_on_stream_exhaustion(tmp_path):
    keep = tmp_path / "t.md"
    cmd_chat.run_cli(
        "public",
        str(keep),
        provider=FakeProvider(["x"]),
        input_stream=iter(["hello"]),
        output_stream=io.StringIO(),
    )
    # after one turn, stream is exhausted, session ends
    transcript = keep.read_text()
    assert "hello" in transcript
    assert "**You:** hello" in transcript


def test_run_dispatches_to_cli_with_defaults(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cmd_chat, "default_keep_name", lambda: "fixed.md")

    class _Prov:
        def stream(self, system, messages, *, temperature, max_tokens):
            yield "ok"

    code = cmd_chat.run(
        web=False,
        persona="student",
        keep=None,
        provider=_Prov(),
        input_stream=iter(["hi", "/quit"]),
        output_stream=io.StringIO(),
    )
    assert code == 0
    assert Path(tmp_path / "fixed.md").exists()


def test_run_cli_constructs_default_provider(monkeypatch, tmp_path):
    # exercises the provider-None construction branch without network
    sentinel = FakeProvider(["x"])
    monkeypatch.setattr(cmd_chat, "LiteLLMProvider", lambda model: sentinel)
    code = cmd_chat.run(
        web=False,
        persona="student",
        keep=str(tmp_path / "k.md"),
        input_stream=iter([""]),
        output_stream=io.StringIO(),
    )
    assert code == 0


def test_default_keep_name_format():
    name = cmd_chat.default_keep_name()
    assert name.startswith("amt-")
    assert name.endswith(".md")
    assert len(name) == len("amt-YYYYMMDD-HHMMSS.md")


def test_run_web_launches_both_and_kills_them(monkeypatch):
    launched, killed = [], []

    class _Proc:
        def __init__(self, cmd):
            self.cmd = cmd
            self.pid = 1234

        def wait(self):
            return 0

    def fake_launch(cmd):
        p = _Proc(cmd)
        launched.append(cmd)
        return p

    def fake_killpg(proc):
        killed.append(proc.cmd)

    code = cmd_chat.run_web(
        launch=fake_launch, killpg=fake_killpg, backend_port=8001, frontend_port=5174
    )
    assert code == 0
    assert any("uvicorn" in " ".join(c) for c in launched)
    assert any("dev" in " ".join(c) for c in launched)
    assert len(killed) == 2  # both torn down


def test_run_web_tears_down_on_keyboard_interrupt(monkeypatch):
    killed = []

    class _Proc:
        pid = 1

        def __init__(self, cmd):
            self.cmd = cmd

        def wait(self):
            raise KeyboardInterrupt

    code = cmd_chat.run_web(launch=lambda cmd: _Proc(cmd), killpg=lambda p: killed.append(p))
    assert code == 0
    assert len(killed) == 2


def test_default_launch_and_killpg_manage_a_real_process():
    # Covers the real _launch/_killpg using a short-lived child in its own session.
    proc = cmd_chat._launch(["sleep", "30"])
    try:
        assert proc.pid > 0
        cmd_chat._killpg(proc)
        proc.wait(timeout=5)
        assert proc.returncode is not None
    finally:
        if proc.poll() is None:  # pragma: no cover - safety net
            proc.kill()


def test_run_dispatches_to_web(monkeypatch):
    monkeypatch.setattr(cmd_chat, "run_web", lambda **kw: 42)
    assert cmd_chat.run(web=True, persona="student", keep=None) == 42
