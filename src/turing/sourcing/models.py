from dataclasses import dataclass


@dataclass(frozen=True)
class SourceEntry:
    ref: str
    title: str | None = None
    type: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class ItemMetadata:
    ref: str
    date: str | None
    description: str | None
    copyright: str | None
    provenance: str | None
    source_url: str


@dataclass(frozen=True)
class FetchResult:
    html: str
    pdf_url: str | None
    pdf_bytes: bytes | None


@dataclass(frozen=True)
class RunResult:
    ref: str
    status: str
    path: str | None = None
    error: str | None = None
