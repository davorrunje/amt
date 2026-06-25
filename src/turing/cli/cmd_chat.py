import os
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from turing.api.config import Settings
from turing.core.chat import ChatSession
from turing.core.provider import LiteLLMProvider, Message


def default_keep_name() -> str:
    return f"amt-{datetime.now():%Y%m%d-%H%M%S}.md"


def run_cli(persona, keep_path, *, provider, input_stream, output_stream) -> int:
    session = ChatSession(provider)
    history: list[Message] = []
    transcript = [f"# Conversation with Turing ({persona})", ""]
    for raw in input_stream:
        user = raw.strip()
        if user in ("", "/quit", "/exit"):
            break
        history.append(Message("user", user))
        reply = ""
        for chunk in session.stream_reply(persona, history):
            output_stream.write(chunk)
            reply += chunk
        output_stream.write("\n")
        history.append(Message("assistant", reply))
        transcript += [f"**You:** {user}", "", f"**Turing:** {reply}", ""]
    Path(keep_path).write_text("\n".join(transcript), encoding="utf-8")
    return 0


def _launch(cmd: list[str]) -> subprocess.Popen:
    return subprocess.Popen(cmd, start_new_session=True)


def _killpg(proc: subprocess.Popen) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except ProcessLookupError:  # pragma: no cover - already exited
        pass


def run_web(*, launch=_launch, killpg=_killpg, backend_port=8000, frontend_port=5174) -> int:
    procs: list[subprocess.Popen] = []
    backend_cmd = [
        "uv",
        "run",
        "uvicorn",
        "turing.api.app:app",
        "--reload",
        "--port",
        str(backend_port),
    ]
    frontend_cmd = ["npm", "--prefix", "frontend", "run", "dev", "--", "--port", str(frontend_port)]
    try:
        procs.append(launch(backend_cmd))
        procs.append(launch(frontend_cmd))
        print(
            f"backend http://localhost:{backend_port}"
            f"  frontend http://localhost:{frontend_port}"
            f"  (Ctrl+C to stop)"
        )
        procs[0].wait()
        return 0
    except KeyboardInterrupt:
        return 0
    finally:
        for proc in procs:
            killpg(proc)


def run(args, *, provider=None, input_stream=None, output_stream=None) -> int:
    if args.web:
        return run_web()
    keep = args.keep or default_keep_name()
    if provider is None:
        provider = LiteLLMProvider(Settings().model)
    return run_cli(
        args.persona,
        keep,
        provider=provider,
        input_stream=input_stream if input_stream is not None else sys.stdin,
        output_stream=output_stream if output_stream is not None else sys.stdout,
    )
