import sys

from turing.sourcing.__main__ import run_sourcing


def run(*, model: str, force: bool, browser=None, transcriber=None) -> int:
    code = run_sourcing(model=model, force=force, browser=browser, transcriber=transcriber)
    if code != 0:
        print(
            "\nIf an item failed: ensure Chromium is installed (uv run playwright install chromium)"
            " and GEMINI_API_KEY is set.",
            file=sys.stderr,
        )
    return code
