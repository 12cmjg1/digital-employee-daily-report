import json
from pathlib import Path
from typing import Any


def ensure_parent(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def save_text(path: str | Path, text: str) -> None:
    target = ensure_parent(path)
    target.write_text(text, encoding="utf-8")


def save_json(path: str | Path, data: Any) -> None:
    target = ensure_parent(path)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: str | Path) -> Any:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"JSON file not found: {target.resolve()}")
    return json.loads(target.read_text(encoding="utf-8"))
