from pathlib import Path

_PROMPT_PATH = Path(__file__).parent / "service_prompt.md"


def get_service_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")
