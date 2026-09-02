"""
Provider/task router with optional fallbacks.

The default pipeline is free-by-default: if no model API keys are configured,
callers should fall back to deterministic logic rather than failing.
"""
import os
import time
from dataclasses import dataclass

from .config import routing as load_routing


@dataclass
class ModelResult:
    provider: str
    model: str
    text: str


class Router:
    DEFAULT_PRIORITY = {
        "research": {"gemini": 1, "groq": 2, "openrouter": 3},
        "generation": {"gemini": 1, "groq": 2, "openrouter": 3},
        "critic": {"groq": 1, "gemini": 2, "openrouter": 3},
    }

    def __init__(self):
        self.providers = []
        self.cfg = load_routing()
        self._load()

    def _env_key(self, provider):
        return {
            "gemini": "GEMINI_API_KEY",
            "groq": "GROQ_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }[provider]

    def _default_model(self, provider):
        return {
            "gemini": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            "groq": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            "openrouter": os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b"),
        }[provider]

    def _priority(self, provider, task):
        provider_cfg = (self.cfg.get("providers") or {}).get(provider, {})
        priority = (provider_cfg.get("priority") or {}).get(task)
        if priority is not None:
            return priority
        return self.DEFAULT_PRIORITY.get(task, {}).get(provider, 99)

    def _load(self):
        provider_cfg = self.cfg.get("providers") or {}
        for provider in ("gemini", "groq", "openrouter"):
            if provider_cfg and not provider_cfg.get(provider, {}).get("enabled", True):
                continue
            key = os.getenv(self._env_key(provider))
            if key:
                self.providers.append((provider, self._default_model(provider)))

    def order(self, task):
        ordered = sorted(
            self.providers,
            key=lambda item: (self._priority(item[0], task), item[0]),
        )
        return ordered

    def available(self, task):
        return self.order(task)

    def call(self, task, prompt, json_mode=False):
        errors = []
        for provider, model in self.order(task):
            try:
                if provider == "gemini":
                    from google import genai
                    from google.genai import types

                    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                    cfg = types.GenerateContentConfig(
                        temperature=0.2,
                        response_mime_type="application/json" if json_mode else "text/plain",
                    )
                    response = client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=cfg,
                    )
                    return ModelResult(provider, model, response.text)

                if provider in {"groq", "openrouter"}:
                    from openai import OpenAI

                    if provider == "groq":
                        base = "https://api.groq.com/openai/v1"
                        key = os.getenv("GROQ_API_KEY")
                    else:
                        base = "https://openrouter.ai/api/v1"
                        key = os.getenv("OPENROUTER_API_KEY")

                    client = OpenAI(api_key=key, base_url=base)
                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.2,
                    )
                    return ModelResult(provider, model, response.choices[0].message.content)
            except Exception as exc:
                errors.append(f"{provider}: {exc}")
                time.sleep(0.5)

        raise RuntimeError("All configured models failed: " + " | ".join(errors))
