from dataclasses import dataclass
from pathlib import Path

import yaml

PERSONAS_DIR = Path(__file__).resolve().parent.parent / "personas"


@dataclass(frozen=True)
class Persona:
    id: str
    name: str
    description: str
    overlay_file: str


def load_registry(personas_dir: Path = PERSONAS_DIR) -> list[Persona]:
    data = yaml.safe_load((personas_dir / "personas.yaml").read_text(encoding="utf-8"))
    return [Persona(**entry) for entry in data["personas"]]


def get_persona(persona_id: str, personas_dir: Path = PERSONAS_DIR) -> Persona:
    for persona in load_registry(personas_dir):
        if persona.id == persona_id:
            return persona
    raise KeyError(persona_id)


def compose_system_prompt(persona_id: str, personas_dir: Path = PERSONAS_DIR) -> str:
    persona = get_persona(persona_id, personas_dir)
    base = (personas_dir / "base.md").read_text(encoding="utf-8")
    overlay = (personas_dir / persona.overlay_file).read_text(encoding="utf-8")
    return f"{base.strip()}\n\n{overlay.strip()}\n"
