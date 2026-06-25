import time
from typing import Protocol

from playwright.sync_api import sync_playwright

from turing.sourcing.models import FetchResult

DEFAULT_USER_AGENT = "VirtualTuring/0.1 (research; +https://github.com/davorrunje/amt)"


class Browser(Protocol):
    def fetch(self, url: str) -> FetchResult: ...


class FakeBrowser:
    def __init__(self, result: FetchResult) -> None:
        self._result = result
        self.last_url: str | None = None

    def fetch(self, url: str) -> FetchResult:
        self.last_url = url
        return self._result


class PlaywrightBrowser:
    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        delay: float = 1.0,
        timeout_ms: int = 60000,
        sleep=time.sleep,
    ) -> None:
        self._user_agent = user_agent
        self._delay = delay
        self._timeout_ms = timeout_ms
        self._sleep = sleep

    def fetch(self, url: str) -> FetchResult:
        captured: dict[str, str] = {}

        def on_response(response):
            ctype = response.headers.get("content-type", "")
            if response.url.lower().endswith(".pdf") or "application/pdf" in ctype:
                captured.setdefault("url", response.url)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=self._user_agent)
            page.on("response", on_response)
            page.goto(url, wait_until="networkidle", timeout=self._timeout_ms)
            html = page.content()
            pdf_url = captured.get("url")
            pdf_bytes = page.request.get(pdf_url).body() if pdf_url else None
            browser.close()

        if self._delay:
            self._sleep(self._delay)
        return FetchResult(html=html, pdf_url=pdf_url, pdf_bytes=pdf_bytes)
