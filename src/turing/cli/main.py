import argparse
import os
from pathlib import Path

from turing.cli import cmd_source


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

    return parser


def main(argv: list[str] | None = None) -> int:
    load_env()
    args = build_parser().parse_args(argv)
    return args.func(args)
