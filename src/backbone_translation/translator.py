import json
from pathlib import Path
from typing import Any


class Translator:
    def __init__(self, phrases: dict[str, str]):
        self._phrases = phrases

    @classmethod
    def from_json_file(cls, path: str) -> "Translator":
        with Path(path).open("r", encoding="utf-8") as file:
            data = json.load(file)
        return cls(data if isinstance(data, dict) else {})

    def translate(self, key: str, **kwargs: Any) -> str:
        phrase = self._phrases.get(key, key)
        if not kwargs:
            return phrase
        try:
            return phrase.format(**kwargs)
        except Exception:
            return phrase
