from turing.sourcing.models import SourceEntry

BASE_URL = "https://turingarchive.kings.cam.ac.uk"


def reference_to_slug(ref: str) -> str:
    return ref.strip().lower().replace("/", "-")


def resolve_url(entry: SourceEntry) -> str:
    if entry.url:
        return entry.url
    return f"{BASE_URL}/{reference_to_slug(entry.ref)}"
