import argparse
import os
from pathlib import Path

from turing.cli import cmd_chat, cmd_personas, cmd_source


def load_env(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="amt", description="Virtual Alan Turing toolkit.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_source = sub.add_parser("source", help="Download + transcribe archive references.")
    p_source.add_argument("--model", default="gemini-2.5-pro")
    p_source.add_argument("--force", action="store_true")
    p_source.set_defaults(func=cmd_source.run)

    p_chat = sub.add_parser("chat", help="Talk to Turing (terminal or web).")
    mode = p_chat.add_mutually_exclusive_group()
    mode.add_argument("--cli", action="store_true", help="Terminal REPL (default).")
    mode.add_argument("--web", action="store_true", help="Launch the web UI.")
    p_chat.add_argument(
        "--persona",
        default="student",
        choices=["student", "public", "colleague"],
    )
    p_chat.add_argument(
        "--keep",
        default=None,
        help="Transcript path (default amt-<timestamp>.md).",
    )
    p_chat.set_defaults(func=cmd_chat.run)

    p_personas = sub.add_parser("personas", help="LLM-build persona candidates from the corpus.")
    p_personas.add_argument(
        "--prompt", default=None, help="Extra instruction appended to every build prompt."
    )
    p_personas.add_argument(
        "--apply", action="store_true", help="Promote staged candidates to live."
    )
    p_personas.set_defaults(func=cmd_personas.run)

    return parser


def main(argv: list[str] | None = None) -> int:
    load_env()
    args = build_parser().parse_args(argv)
    return args.func(args)
