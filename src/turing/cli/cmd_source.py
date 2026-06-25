import sys

from turing.sourcing.__main__ import main as sourcing_main


def run(args, *, browser=None, transcriber=None) -> int:
    argv = ["--model", args.model]
    if args.force:
        argv.append("--force")
    code = sourcing_main(argv, browser=browser, transcriber=transcriber)
    if code != 0:
        print(
            "\nIf an item failed: ensure Chromium is installed (uv run playwright install chromium)"
            " and GEMINI_API_KEY is set.",
            file=sys.stderr,
        )
    return code
