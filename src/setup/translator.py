from pathlib import Path

from backbone_translation.translator import Translator

_SRC_ROOT = Path(__file__).resolve().parent.parent

translator = Translator.from_json_file(str(_SRC_ROOT / "setup" / "phrases.json"))

trans = translator.translate
