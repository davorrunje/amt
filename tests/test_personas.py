import pytest

from turing.core.personas import (
    Persona,
    compose_system_prompt,
    get_persona,
    load_registry,
)


def test_load_registry_returns_three_personas():
    registry = load_registry()
    ids = [p.id for p in registry]
    assert ids == ["student", "public", "colleague"]
    assert all(isinstance(p, Persona) for p in registry)


def test_get_persona_returns_matching_persona():
    persona = get_persona("colleague")
    assert persona.name == "Expert colleague"
    assert persona.overlay_file == "colleague.md"


def test_get_persona_unknown_raises_keyerror():
    with pytest.raises(KeyError):
        get_persona("nonexistent")


def test_compose_system_prompt_combines_base_and_overlay():
    prompt = compose_system_prompt("student")
    assert "You are Alan Turing" in prompt  # from base
    assert "a student who is still learning" in prompt  # from student overlay
    # base comes before overlay
    assert prompt.index("You are Alan Turing") < prompt.index("a student who is still learning")


def test_compose_system_prompt_unknown_raises_keyerror():
    with pytest.raises(KeyError):
        compose_system_prompt("nonexistent")
