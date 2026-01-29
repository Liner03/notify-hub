import os
import re
from typing import Any, Dict

import yaml


_env_pattern = re.compile(r"\$\{([A-Za-z0-9_]+)\}")


def _substitute_env(value: Any) -> Any:
    if isinstance(value, str):
        def replace(match: re.Match) -> str:
            name = match.group(1)
            env_value = os.getenv(name)
            if env_value is None:
                raise KeyError(f"missing env var: {name}")
            return env_value

        return _env_pattern.sub(replace, value)

    if isinstance(value, list):
        return [_substitute_env(item) for item in value]

    if isinstance(value, dict):
        return {key: _substitute_env(val) for key, val in value.items()}

    return value


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if "notify" not in data:
        raise ValueError("config missing 'notify' root")

    return _substitute_env(data["notify"])
