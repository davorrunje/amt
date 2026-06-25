import io
from pathlib import Path
from types import SimpleNamespace

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

    args = SimpleNamespace(web=False, persona="student", keep=None)
    code = cmd_chat.run(
        args,
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
    args = SimpleNamespace(web=False, persona="student", keep=str(tmp_path / "k.md"))
    code = cmd_chat.run(args, input_stream=iter([""]), output_stream=io.StringIO())
    assert code == 0


def test_default_keep_name_format():
    name = cmd_chat.default_keep_name()
    assert name.startswith("amt-")
    assert name.endswith(".md")
    assert len(name) == len("amt-YYYYMMDD-HHMMSS.md")
