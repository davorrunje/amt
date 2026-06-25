import io
from types import SimpleNamespace

import pytest

from turing.cli import cmd_personas
from turing.core.provider import FakeProvider


def _setup(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "amt-d-4.md").write_text("Dear Robin, the structure causes worries.")
    personas = tmp_path / "personas"
    personas.mkdir()
    for name in ("base.md", "student.md", "public.md", "colleague.md"):
        (personas / name).write_text(f"OLD {name}\n")
    cfg = tmp_path / "build-personas.yaml"
    cfg.write_text(
        "sources:\n  - AMT/D/4\n"
        "personas:\n"
        "  base: {file: base.md, prompt: 'write base'}\n"
        "  student: {file: student.md, prompt: 'write student'}\n"
        "  public: {file: public.md, prompt: 'write public'}\n"
        "  colleague: {file: colleague.md, prompt: 'write colleague'}\n"
    )
    return corpus, personas, cfg


def test_load_sources_concatenates(tmp_path):
    corpus, _, _ = _setup(tmp_path)
    text = cmd_personas.load_sources(["AMT/D/4"], corpus)
    assert "Dear Robin" in text


def test_load_sources_missing_raises(tmp_path):
    corpus, _, _ = _setup(tmp_path)
    with pytest.raises(FileNotFoundError, match="AMT/X/9"):
        cmd_personas.load_sources(["AMT/X/9"], corpus)


def test_run_writes_candidates_and_diff_without_touching_live(tmp_path):
    corpus, personas, cfg = _setup(tmp_path)
    candidates = tmp_path / "candidates"
    out = io.StringIO()
    code = cmd_personas.run(
        SimpleNamespace(prompt=None, apply=False),
        provider=FakeProvider(["NEW base content\n"]),
        build_config_path=cfg,
        corpus_dir=corpus,
        personas_dir=personas,
        candidates_dir=candidates,
        output_stream=out,
    )
    assert code == 0
    assert (candidates / "base.md").read_text() == "NEW base content\n"
    assert (personas / "base.md").read_text() == "OLD base.md\n"  # live untouched
    assert "NEW base content" in out.getvalue()  # diff shown


def test_run_appends_extra_prompt(tmp_path):
    corpus, personas, cfg = _setup(tmp_path)

    class _Spy:
        def __init__(self):
            self.systems = []

        def stream(self, system, messages, *, temperature, max_tokens):
            self.systems.append(system)
            yield "x"

    spy = _Spy()
    cmd_personas.run(
        SimpleNamespace(prompt="BE TERSE", apply=False),
        provider=spy,
        build_config_path=cfg,
        corpus_dir=corpus,
        personas_dir=personas,
        candidates_dir=tmp_path / "candidates",
        output_stream=io.StringIO(),
    )
    assert all("BE TERSE" in s for s in spy.systems)


def test_apply_promotes_candidates(tmp_path):
    _, personas, cfg = _setup(tmp_path)
    candidates = tmp_path / "candidates"
    candidates.mkdir()
    (candidates / "base.md").write_text("PROMOTED\n")
    code = cmd_personas.run(
        SimpleNamespace(prompt=None, apply=True),
        build_config_path=cfg,
        personas_dir=personas,
        candidates_dir=candidates,
        output_stream=io.StringIO(),
    )
    assert code == 0
    assert (personas / "base.md").read_text() == "PROMOTED\n"


def test_run_default_provider_constructed(monkeypatch, tmp_path):
    corpus, personas, cfg = _setup(tmp_path)
    monkeypatch.setattr(cmd_personas, "LiteLLMProvider", lambda model: FakeProvider(["y\n"]))
    code = cmd_personas.run(
        SimpleNamespace(prompt=None, apply=False),
        build_config_path=cfg,
        corpus_dir=corpus,
        personas_dir=personas,
        candidates_dir=tmp_path / "candidates",
        output_stream=io.StringIO(),
    )
    assert code == 0
