from pathlib import Path

from turing.sourcing.metadata import parse_metadata

FIXTURE = (Path(__file__).parent / "fixtures" / "item_synthetic.html").read_text()


def test_parses_ref_from_h1():
    meta = parse_metadata(FIXTURE, "https://x.test/amt-c-10")
    assert meta.ref == "AMT/C/10"
    assert meta.source_url == "https://x.test/amt-c-10"


def test_parses_copyright_and_provenance():
    meta = parse_metadata(FIXTURE, "https://x.test/amt-c-10")
    assert meta.copyright == "Copyright (c) Example College."
    assert meta.provenance == "Assembled after the author's death."


def test_description_excludes_labeled_fields_and_finds_date():
    meta = parse_metadata(FIXTURE, "https://x.test/amt-c-10")
    assert meta.description is not None
    assert "Sample scope and content" in meta.description
    assert "Paper, 16 sh." in meta.description
    assert "Provenance:" not in meta.description
    assert meta.date == "[After 1954]"


def test_missing_fields_are_none():
    html = "<html><body><h1>AMT/X/1</h1><article><p>No date here.</p></article></body></html>"
    meta = parse_metadata(html, "https://x.test/amt-x-1")
    assert meta.ref == "AMT/X/1"
    assert meta.date is None
    assert meta.copyright is None
    assert meta.provenance is None
    assert meta.description == "No date here."


def test_coverage_labeled_fields():
    """Ensure the labeled field extraction branch is covered."""
    html = (
        "<html><body><h1>REF</h1><article>"
        "<p>Regular paragraph without date.</p>"
        "<p><strong>Provenance:</strong> Test prov</p>"
        "<p><strong>Copyright:</strong> Test copy</p>"
        "</article></body></html>"
    )
    meta = parse_metadata(html, "https://test.url")
    assert meta.provenance == "Test prov"
    assert meta.copyright == "Test copy"
    assert meta.description == "Regular paragraph without date."
    assert meta.date is None


def test_no_article_tag():
    """Test when article tag is missing."""
    html = "<html><body><h1>REF</h1><p>No article here.</p></body></html>"
    meta = parse_metadata(html, "https://test.url")
    assert meta.ref == "REF"
    assert meta.copyright is None
    assert meta.provenance is None
    assert meta.description is None
    assert meta.date is None
