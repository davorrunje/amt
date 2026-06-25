from pathlib import Path

import typer

from turing.sourcing.browser import PlaywrightBrowser
from turing.sourcing.pipeline import load_sources, run
from turing.sourcing.transcriber import GeminiTranscriber

app = typer.Typer(help="Transcribe curated archive items.")


def run_sourcing(
    *,
    model: str = "gemini-2.5-pro",
    force: bool = False,
    sources: str = "corpus/sources.yaml",
    corpus_dir: str = "corpus",
    cache_dir: str = "corpus/cache",
    browser=None,
    transcriber=None,
) -> int:
    if browser is None:
        browser = PlaywrightBrowser()
    if transcriber is None:
        transcriber = GeminiTranscriber(model=model)
    results = run(
        load_sources(Path(sources)),
        browser=browser,
        transcriber=transcriber,
        corpus_dir=Path(corpus_dir),
        cache_dir=Path(cache_dir),
        force=force,
    )
    for result in results:
        suffix = f" ({result.error})" if result.error else ""
        print(f"{result.ref}: {result.status}{suffix}")
    return 1 if any(r.status == "error" for r in results) else 0


@app.callback(invoke_without_command=True)
def _main(
    model: str = "gemini-2.5-pro",
    force: bool = False,
    sources: str = "corpus/sources.yaml",
    corpus_dir: str = "corpus",
    cache_dir: str = "corpus/cache",
) -> None:
    raise typer.Exit(
        run_sourcing(
            model=model, force=force, sources=sources, corpus_dir=corpus_dir, cache_dir=cache_dir
        )
    )


def main() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
