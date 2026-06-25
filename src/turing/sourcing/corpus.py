from pathlib import Path

import yaml

from turing.sourcing.models import ItemMetadata, SourceEntry
from turing.sourcing.resolver import reference_to_slug


def corpus_path(ref: str, corpus_dir: Path) -> Path:
    return corpus_dir / f"{reference_to_slug(ref)}.md"


def is_done(ref: str, corpus_dir: Path) -> bool:
    return corpus_path(ref, corpus_dir).exists()


def write_item(
    entry: SourceEntry,
    metadata: ItemMetadata,
    transcription: str,
    corpus_dir: Path,
) -> Path:
    corpus_dir.mkdir(parents=True, exist_ok=True)
    front = {
        "ref": metadata.ref or entry.ref,
        "title": entry.title or metadata.ref or entry.ref,
        "type": entry.type or "unknown",
        "date": metadata.date,
        "source_url": metadata.source_url,
        "copyright": metadata.copyright,
    }
    text = "---\n" + yaml.safe_dump(front, sort_keys=False) + "---\n\n" + transcription
    path = corpus_path(entry.ref, corpus_dir)
    path.write_text(text, encoding="utf-8")
    return path
