from types import SimpleNamespace

from turing.sourcing import browser as browser_module
from turing.sourcing.browser import FakeBrowser, PlaywrightBrowser
from turing.sourcing.models import FetchResult


def test_fakebrowser_returns_result_and_records_url():
    result = FetchResult(html="<h1>x</h1>", pdf_url="https://x/y.pdf", pdf_bytes=b"%PDF")
    fake = FakeBrowser(result)
    assert fake.fetch("https://x/page") is result
    assert fake.last_url == "https://x/page"


class _Resp:
    def __init__(self, url, ctype):
        self.url = url
        self.headers = {"content-type": ctype}


class _Req:
    def __init__(self, body):
        self._body = body
        self.requested = None

    def get(self, url):
        self.requested = url
        return self

    def body(self):
        return self._body


class _Page:
    def __init__(self, html, responses, pdf_body):
        self._html = html
        self._responses = responses
        self.request = _Req(pdf_body)
        self._handlers = {}

    def on(self, event, handler):
        self._handlers[event] = handler

    def goto(self, url, **kwargs):
        for resp in self._responses:
            self._handlers["response"](resp)

    def content(self):
        return self._html


class _Browser:
    def __init__(self, page):
        self._page = page
        self.closed = False

    def new_page(self, **kwargs):
        return self._page

    def close(self):
        self.closed = True


def _fake_playwright(page):
    browser = _Browser(page)
    chromium = SimpleNamespace(launch=lambda **kw: browser)
    pw = SimpleNamespace(chromium=chromium)

    class _CM:
        def __enter__(self):
            return pw

        def __exit__(self, *a):
            return False

    return lambda: _CM()


def test_playwrightbrowser_captures_pdf(monkeypatch):
    page = _Page("<h1>doc</h1>", [_Resp("https://x/scan.pdf", "application/pdf")], b"%PDF-bytes")
    monkeypatch.setattr(browser_module, "sync_playwright", _fake_playwright(page))
    slept = []
    pb = PlaywrightBrowser(delay=0.5, sleep=lambda s: slept.append(s))
    result = pb.fetch("https://x/amt-c-10")
    assert result.html == "<h1>doc</h1>"
    assert result.pdf_url == "https://x/scan.pdf"
    assert result.pdf_bytes == b"%PDF-bytes"
    assert slept == [0.5]


def test_playwrightbrowser_no_pdf(monkeypatch):
    page = _Page("<h1>doc</h1>", [_Resp("https://x/style.css", "text/css")], b"unused")
    monkeypatch.setattr(browser_module, "sync_playwright", _fake_playwright(page))
    pb = PlaywrightBrowser(delay=0, sleep=lambda s: None)
    result = pb.fetch("https://x/amt-c-10")
    assert result.pdf_url is None
    assert result.pdf_bytes is None
