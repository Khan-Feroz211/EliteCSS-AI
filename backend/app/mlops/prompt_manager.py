from pathlib import Path
import random

import yaml

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"


def load_prompt(version: str) -> str:
    path = PROMPT_DIR / f"css_prep_{version}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Prompt version not found: {version}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    system_prompt = data.get("system_prompt", "").strip()
    if not system_prompt:
        raise ValueError(f"Prompt file is invalid: {path}")
    return system_prompt


def select_prompt_version() -> str:
    return "v1" if random.random() < 0.5 else "v2"


def detect_exam_topic(messages: list[dict[str, str]]) -> str:
    text = " ".join(m.get("content", "") for m in messages).lower()
    topic_map = {
        "pakistan affairs": ["pakistan", "governance", "constitution", "foreign policy"],
        "history": ["history", "movement", "partition", "mughal"],
        "current affairs": ["current affairs", "news", "economy", "geopolitics"],
        "essay": ["essay", "outline", "thesis", "argument"],
        "general knowledge": ["general knowledge", "gk", "science", "capital"],
    }

    for topic, keywords in topic_map.items():
        if any(k in text for k in keywords):
            return topic
    return "unknown"
