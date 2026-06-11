from pathlib import Path
from typing import Any

import yaml


def load_config(path: str = "config.yaml") -> dict[str, Any]:
    """Load YAML config file."""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path.resolve()}")

    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    required_sections = ["project", "runtime", "keywords", "sources", "report"]
    missing = [section for section in required_sections if section not in config]
    if missing:
        raise ValueError(f"Config file is missing sections: {', '.join(missing)}")
    return config
