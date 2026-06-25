import difflib
import shutil
import sys
from pathlib import Path

import yaml

from turing.api.config import Settings
from turing.core.personas import PERSONAS_DIR
from turing.core.provider import LiteLLMProvider, Message
from turing.sourcing.resolver import reference_to_slug

BUILD_CONFIG = PERSONAS_DIR / "build-personas.yaml"
CANDIDATES_DIR = PERSONAS_DIR / "candidates"
CORPUS_DIR = Path("corpus")


def load_build_config(path: Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load_sources(refs: list[str], corpus_dir: Path) -> str:
    parts = []
    for ref in refs:
        md = corpus_dir / f"{reference_to_slug(ref)}.md"
        if not md.exists():
            raise FileNotFoundError(f"transcription missing for {ref} (run `amt source` first)")
        parts.append(md.read_text(encoding="utf-8"))
    return "\n\n".join(parts)


def run(
    args,
    *,
    provider=None,
    build_config_path: Path | None = None,
    corpus_dir: Path | None = None,
    personas_dir: Path | None = None,
    candidates_dir: Path | None = None,
    output_stream=None,
) -> int:
    config_path = build_config_path or BUILD_CONFIG
    personas_dir = personas_dir or PERSONAS_DIR
    candidates_dir = candidates_dir or CANDIDATES_DIR
    out = output_stream if output_stream is not None else sys.stdout
    config = load_build_config(config_path)

    if args.apply:
        missing = [
            spec["file"]
            for spec in config["personas"].values()
            if not (candidates_dir / spec["file"]).exists()
        ]
        if missing:
            print(f"Missing candidates: {', '.join(missing)}. Run `amt personas` first.", file=out)
            return 1
        for spec in config["personas"].values():
            shutil.copyfile(candidates_dir / spec["file"], personas_dir / spec["file"])
        print("Applied candidates to live personas.", file=out)
        return 0

    corpus_dir = corpus_dir or CORPUS_DIR
    sources_text = load_sources(config["sources"], corpus_dir)
    if provider is None:
        provider = LiteLLMProvider(Settings().model)
    candidates_dir.mkdir(parents=True, exist_ok=True)

    for spec in config["personas"].values():
        system = spec["prompt"]
        if args.prompt:
            system = f"{system}\n\n{args.prompt}"
        text = "".join(
            provider.stream(
                system,
                [Message("user", sources_text)],
                temperature=0.7,
                max_tokens=4096,
            )
        )
        candidate = candidates_dir / spec["file"]
        candidate.write_text(text, encoding="utf-8")
        live = personas_dir / spec["file"]
        old = live.read_text(encoding="utf-8").splitlines(keepends=True) if live.exists() else []
        diff = difflib.unified_diff(
            old,
            text.splitlines(keepends=True),
            fromfile=f"live/{spec['file']}",
            tofile=f"candidate/{spec['file']}",
        )
        print("".join(diff), file=out)

    print(
        f"\nWrote candidates to {candidates_dir}. Review, then run `amt personas --apply`.",
        file=out,
    )
    return 0
