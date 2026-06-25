from turing.sourcing.models import SourceEntry
from turing.sourcing.resolver import BASE_URL, reference_to_slug, resolve_url


def test_reference_to_slug():
    assert reference_to_slug("AMT/C/10") == "amt-c-10"
    assert reference_to_slug(" AMT/K/1/77 ") == "amt-k-1-77"


def test_resolve_url_default():
    assert resolve_url(SourceEntry(ref="AMT/C/10")) == f"{BASE_URL}/amt-c-10"


def test_resolve_url_override():
    entry = SourceEntry(ref="AMT/K/1/77", url="https://x.test/longer/slug")
    assert resolve_url(entry) == "https://x.test/longer/slug"
