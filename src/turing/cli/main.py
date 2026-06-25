import os
from enum import StrEnum
from pathlib import Path

import typer

from turing.cli import cmd_chat, cmd_personas, cmd_source

app = typer.Typer(help="Virtual Alan Turing toolkit.", no_args_is_help=True)


class Persona(StrEnum):
    student = "student"
    public = "public"
    colleague = "colleague"


def load_env(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


@app.callback()
def _root() -> None:
    load_env()


@app.command(help="Download + transcribe archive references.")
def source(model: str = "gemini-2.5-pro", force: bool = False) -> None:
    raise typer.Exit(cmd_source.run(model=model, force=force))


@app.command(help="Talk to Turing (terminal by default, or --web).")
def chat(
    web: bool = False,
    persona: Persona = Persona.student,
    keep: str | None = None,
) -> None:
    raise typer.Exit(cmd_chat.run(web=web, persona=persona.value, keep=keep))


@app.command(help="LLM-build persona candidates from the corpus.")
def personas(prompt: str | None = None, apply: bool = False) -> None:
    raise typer.Exit(cmd_personas.run(prompt=prompt, apply=apply))


def main() -> None:
    app()
