from pathlib import Path
import os, yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / ".env.local", override=True)


def _merge_dicts(base, override):
    if not isinstance(base, dict) or not isinstance(override, dict):
        return override

    merged = dict(base)
    for key, value in override.items():
        if key in merged:
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged

def load_yaml(name):
    base_path = ROOT / "config" / name
    local_path = base_path.with_name(f"{base_path.stem}.local{base_path.suffix}")

    with open(base_path, encoding="utf-8") as f:
        base = yaml.safe_load(f) or {}

    if local_path.exists():
        with open(local_path, encoding="utf-8") as f:
            override = yaml.safe_load(f) or {}
        return _merge_dicts(base, override)

    return base

def settings():
    return load_yaml("settings.yml")

def profile():
    return load_yaml("profile.yml")

def scoring():
    return load_yaml("scoring.yml")

def routing():
    return load_yaml("routing.yml")
