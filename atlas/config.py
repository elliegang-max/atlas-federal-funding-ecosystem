"""Environment and API client setup.

The grader's `.env` sits one folder *above* the cloned repo, so `find_env_file`
checks the repo root first and then walks up. Nothing here reads a key from
anywhere else, and no key is ever logged.
"""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

from openai import AsyncOpenAI, OpenAI

REPO_ROOT = Path(__file__).resolve().parent.parent

# Only model the course key is permitted to use.
MODEL = "gpt-6-luna"

PORTKEY_BASE_URL = "https://api.portkey.ai/v1"


def find_env_file() -> Path | None:
    """Repo root first, then up to three parent folders."""
    candidates = [REPO_ROOT / ".env"]
    parent = REPO_ROOT
    for _ in range(3):
        parent = parent.parent
        candidates.append(parent / ".env")
    return next((p for p in candidates if p.is_file()), None)


def _parse_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        out[name.strip()] = value.strip().strip('"').strip("'")
    return out


@lru_cache(maxsize=1)
def load_credentials() -> tuple[str, str]:
    """Return (portkey_api_key, base_url). Environment wins over the .env file."""
    key = os.environ.get("PORTKEY_API_KEY")
    base_url = os.environ.get("PORTKEY_BASE_URL", PORTKEY_BASE_URL)

    if not key:
        env_path = find_env_file()
        if env_path:
            values = _parse_env(env_path)
            key = values.get("PORTKEY_API_KEY")
            base_url = values.get("PORTKEY_BASE_URL", base_url)

    if not key:
        sys.exit(
            "PORTKEY_API_KEY is not set.\n"
            "Put it in a .env file in this folder or the folder above, "
            "or export it in your shell. See .env.example."
        )
    return key, base_url


def make_async_client() -> AsyncOpenAI:
    key, base_url = load_credentials()
    return AsyncOpenAI(
        base_url=base_url,
        api_key="unused",  # Portkey authenticates with its own header
        default_headers={"x-portkey-api-key": key},
        timeout=240.0,
    )


def make_sync_client() -> OpenAI:
    key, base_url = load_credentials()
    return OpenAI(
        base_url=base_url,
        api_key="unused",
        default_headers={"x-portkey-api-key": key},
        timeout=240.0,
    )
