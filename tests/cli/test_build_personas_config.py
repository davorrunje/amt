import yaml

from turing.core.personas import PERSONAS_DIR


def test_base_persona_prompt_contains_guardrail_markers():
    build_yaml = PERSONAS_DIR / "build-personas.yaml"
    data = yaml.safe_load(build_yaml.read_text(encoding="utf-8"))
    base_prompt = data["personas"]["base"]["prompt"].lower()
    assert "reconstruction" in base_prompt, "guardrail 'reconstruction' missing from base prompt"
    assert "never invent" in base_prompt, "guardrail 'never invent' missing from base prompt"
    assert "extrapolation" in base_prompt, "guardrail 'extrapolation' missing from base prompt"
