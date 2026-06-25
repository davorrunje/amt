import yaml

from turing.sourcing.corpus import corpus_path, is_done, write_item
from turing.sourcing.models import ItemMetadata, SourceEntry


def _meta(ref="AMT/C/10"):
    return ItemMetadata(
        ref=ref,
        date="[After 1954]",
        description="desc",
        copyright="Copyright (c) Example.",
        provenance="prov",
        source_url="https://x.test/amt-c-10",
    )


def test_corpus_path_uses_slug(tmp_path):
    assert corpus_path("AMT/C/10", tmp_path) == tmp_path / "amt-c-10.md"


def test_is_done_false_then_true(tmp_path):
    entry = SourceEntry(ref="AMT/C/10", title="Morphogenesis", type="ms")
    assert is_done("AMT/C/10", tmp_path) is False
    write_item(entry, _meta(), "the transcription", tmp_path)
    assert is_done("AMT/C/10", tmp_path) is True


def test_write_item_front_matter_and_body(tmp_path):
    entry = SourceEntry(ref="AMT/C/10", title="Morphogenesis", type="ms")
    path = write_item(entry, _meta(), "BODY TEXT", tmp_path)
    text = path.read_text()
    assert text.startswith("---\n")
    front, body = text.split("---\n", 2)[1:]
    meta = yaml.safe_load(front)
    assert meta["ref"] == "AMT/C/10"
    assert meta["title"] == "Morphogenesis"
    assert meta["type"] == "ms"
    assert meta["date"] == "[After 1954]"
    assert meta["source_url"] == "https://x.test/amt-c-10"
    assert "BODY TEXT" in body


def test_write_item_title_and_type_fallback(tmp_path):
    entry = SourceEntry(ref="AMT/X/1")  # no title/type
    path = write_item(entry, _meta(ref="AMT/X/1"), "b", tmp_path)
    meta = yaml.safe_load(path.read_text().split("---\n", 2)[1])
    assert meta["title"] == "AMT/X/1"
    assert meta["type"] == "unknown"
