from __future__ import annotations

from urllib.parse import urlparse

from .config import settings


class PolicyError(ValueError):
    pass


class NetworkPolicy:
    def __init__(self, allowed_domains: list[str] | None = None) -> None:
        self.allowed_domains = allowed_domains or settings.allowed_domains

    def validate_url(self, url: str) -> None:
        host = urlparse(url).hostname or ""
        if host not in self.allowed_domains:
            raise PolicyError(f"Network call blocked for domain: {host}")
