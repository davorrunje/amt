from turing.sourcing.models import FetchResult, ItemMetadata, RunResult, SourceEntry


def test_source_entry_defaults():
    entry = SourceEntry(ref="AMT/C/10")
    assert entry.ref == "AMT/C/10"
    assert entry.title is None
    assert entry.type is None
    assert entry.url is None


def test_item_metadata_fields():
    meta = ItemMetadata(
        ref="AMT/C/10",
        date="[After 1954]",
        description="A solution of the morphogenetical equations.",
        copyright="Copyright (c) King's College Cambridge.",
        provenance="Assembled after AMT's death.",
        source_url="https://example.test/amt-c-10",
    )
    assert meta.ref == "AMT/C/10"
    assert meta.date == "[After 1954]"


def test_fetch_and_run_results():
    fr = FetchResult(html="<html></html>", pdf_url="https://x/y.pdf", pdf_bytes=b"%PDF")
    assert fr.pdf_bytes == b"%PDF"
    rr = RunResult(ref="AMT/C/10", status="written", path="corpus/amt-c-10.md")
    assert rr.status == "written"
    assert rr.error is None
