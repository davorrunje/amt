import argparse
from pathlib import Path

from turing.sourcing.browser import PlaywrightBrowser
from turing.sourcing.pipeline import load_sources, run
from turing.sourcing.transcriber import GeminiTranscriber


def main(argv: list[str] | None = None, *, browser=None, transcriber=None) -> int:
    parser = argparse.ArgumentParser(
        prog="turing.sourcing", description="Transcribe curated archive items."
    )
    parser.add_argument("--sources", default="corpus/sources.yaml")
    parser.add_argument("--corpus-dir", default="corpus")
    parser.add_argument("--cache-dir", default="corpus/cache")
    parser.add_argument("--model", default="gemini-2.5-pro")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    if browser is None:
        browser = PlaywrightBrowser()
    if transcriber is None:
        transcriber = GeminiTranscriber(model=args.model)

    results = run(
        load_sources(Path(args.sources)),
        browser=browser,
        transcriber=transcriber,
        corpus_dir=Path(args.corpus_dir),
        cache_dir=Path(args.cache_dir),
        force=args.force,
    )
    for result in results:
        suffix = f" ({result.error})" if result.error else ""
        print(f"{result.ref}: {result.status}{suffix}")
    return 1 if any(r.status == "error" for r in results) else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
