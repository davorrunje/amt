import re

from bs4 import BeautifulSoup

from turing.sourcing.models import ItemMetadata

_DATE_RE = re.compile(r"\[[^\]]*\d{4}[^\]]*\]")
_LABELS = ("Provenance:", "Copyright:")


def _labeled(article, label: str) -> str | None:
    for p in article.find_all("p"):
        strong = p.find("strong")
        if strong and strong.get_text(strip=True).rstrip(":") == label.rstrip(":"):
            text = p.get_text(" ", strip=True)
            return text[len(strong.get_text(strip=True)) :].strip()
    return None


def parse_metadata(html: str, source_url: str) -> ItemMetadata:
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    ref = h1.get_text(strip=True) if h1 else ""
    article = soup.find("article")

    copyright_ = provenance = description = None
    if article:
        copyright_ = _labeled(article, "Copyright:")
        provenance = _labeled(article, "Provenance:")
        parts = []
        for p in article.find_all("p"):
            strong = p.find("strong")
            label = strong.get_text(strip=True) if strong else ""
            if label in _LABELS:
                continue
            parts.append(p.get_text(" ", strip=True))
        description = " ".join(parts) if parts else None

    date = None
    if description:
        match = _DATE_RE.search(description)
        date = match.group(0) if match else None

    return ItemMetadata(
        ref=ref,
        date=date,
        description=description,
        copyright=copyright_,
        provenance=provenance,
        source_url=source_url,
    )
