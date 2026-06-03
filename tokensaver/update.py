"""Version and update-check helpers for TokenSaver."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any

from . import __version__

REPOSITORY_URL = "https://github.com/zhangtao-jayce/TokenSaver"
INSTALL_URL = "git+https://github.com/zhangtao-jayce/TokenSaver.git"
PYPROJECT_URL = (
    "https://raw.githubusercontent.com/zhangtao-jayce/TokenSaver/main/pyproject.toml"
)
COMMIT_API_URL = "https://api.github.com/repos/zhangtao-jayce/TokenSaver/commits/main"


@dataclass(frozen=True)
class UpdateInfo:
    local_version: str
    latest_version: str | None
    latest_commit: str | None
    status: str
    upgrade_command: str
    compatibility: list[str]
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def get_version_info() -> dict[str, str]:
    return {
        "name": "tokensaver",
        "version": __version__,
        "repository": REPOSITORY_URL,
    }


def check_for_update(
    *,
    timeout: float = 2.0,
    latest_version: str | None = None,
    latest_commit: str | None = None,
) -> UpdateInfo:
    """Check GitHub main for a newer TokenSaver version.

    The optional latest_version/latest_commit parameters are for tests and
    controlled callers. Normal usage fetches public metadata only.
    """

    error = ""
    if latest_version is None:
        try:
            latest_version = fetch_latest_version(timeout=timeout)
        except (OSError, urllib.error.URLError, TimeoutError, ValueError) as exc:
            error = str(exc)
    if latest_commit is None and latest_version is not None:
        try:
            latest_commit = fetch_latest_commit(timeout=timeout)
        except (OSError, urllib.error.URLError, TimeoutError, ValueError):
            latest_commit = None

    if latest_version is None:
        return UpdateInfo(
            local_version=__version__,
            latest_version=None,
            latest_commit=None,
            status="unknown",
            upgrade_command=_upgrade_command(None),
            compatibility=_compatibility_notes(),
            error=error or "Unable to fetch latest version metadata.",
        )

    status = "update_available" if _version_tuple(latest_version) > _version_tuple(__version__) else "up_to_date"
    return UpdateInfo(
        local_version=__version__,
        latest_version=latest_version,
        latest_commit=latest_commit,
        status=status,
        upgrade_command=_upgrade_command(latest_commit),
        compatibility=_compatibility_notes(),
    )


def fetch_latest_version(*, timeout: float = 2.0) -> str:
    text = _read_url(PYPROJECT_URL, timeout=timeout)
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)
    if not match:
        raise ValueError("Could not parse version from pyproject.toml.")
    return match.group(1)


def fetch_latest_commit(*, timeout: float = 2.0) -> str:
    text = _read_url(COMMIT_API_URL, timeout=timeout)
    payload = json.loads(text)
    sha = str(payload.get("sha") or "")
    if not sha:
        raise ValueError("Could not parse latest commit SHA.")
    return sha[:7]


def format_update_notice(info: UpdateInfo | dict[str, Any] | None) -> str:
    if not info:
        return ""
    data = info.to_dict() if isinstance(info, UpdateInfo) else info
    status = data.get("status")
    if status != "update_available":
        return ""
    latest = data.get("latest_version") or "latest"
    command = data.get("upgrade_command") or _upgrade_command(data.get("latest_commit"))
    return "\n".join(
        [
            "## TokenSaver Update",
            "",
            f"- local_version: {data.get('local_version') or __version__}",
            f"- latest_version: {latest}",
            "- status: update_available",
            "",
            "Upgrade:",
            "",
            "```bash",
            command,
            "```",
        ]
    )


def _read_url(url: str, *, timeout: float) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json,text/plain,*/*",
            "User-Agent": f"tokensaver/{__version__}",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def _upgrade_command(commit: str | None) -> str:
    suffix = f"@{commit}" if commit else ""
    return f"pip install --upgrade --force-reinstall {INSTALL_URL}{suffix}"


def _compatibility_notes() -> list[str]:
    return [
        "Existing local traces remain readable.",
        "New runtime APIs are additive unless release notes say otherwise.",
        "TokenSaver keeps trace data local and fetches only public version metadata.",
    ]


def _version_tuple(version: str) -> tuple[int, int, int]:
    parts = []
    for part in version.split(".")[:3]:
        match = re.match(r"(\d+)", part)
        parts.append(int(match.group(1)) if match else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)  # type: ignore[return-value]
