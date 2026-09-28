from __future__ import annotations

from dataclasses import dataclass, field
from ipaddress import ip_address
from urllib.parse import urlparse


@dataclass
class NetworkTarget:
    scheme: str
    host: str
    port: int
    path_prefix: str = "/"


@dataclass
class NetworkPolicy:
    """Application-level allowlist. It does not replace OS/network controls."""
    allowed: list[NetworkTarget] = field(default_factory=list)
    allow_loopback: bool = True

    def check_url(self, url: str) -> tuple[bool, str]:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False, f"unsupported protocol: {parsed.scheme or '<empty>'}"
        if not parsed.hostname:
            return False, "missing host"
        host = parsed.hostname.lower()
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if self.allow_loopback and host in {"127.0.0.1", "localhost", "::1"}:
            return True, "loopback allowed for local tests"
        for target in self.allowed:
            if target.scheme == parsed.scheme and target.host.lower() == host and target.port == port and parsed.path.startswith(target.path_prefix):
                return True, "approved target"
        return False, "target is not in the deployment allowlist"

    @classmethod
    def from_urls(cls, urls: list[str]) -> "NetworkPolicy":
        targets = []
        for url in urls:
            parsed = urlparse(url)
            if not parsed.hostname:
                continue
            targets.append(NetworkTarget(parsed.scheme, parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), parsed.path or "/"))
        return cls(targets)
