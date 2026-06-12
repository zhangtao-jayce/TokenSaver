"""Installation, upgrade, and environment diagnostics for TokenSaver."""

from __future__ import annotations

import json
import importlib.metadata
import re
import shutil
import site
import subprocess
import sys
import sysconfig
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from . import __version__
from .diagnosis import diagnose_health
from .store import LocalStore
from .update import INSTALL_URL, check_for_update


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    message: str
    evidence: dict[str, Any]
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def verbose_version_info(*, project_dir: str | Path = ".") -> dict[str, Any]:
    package_path = Path(__file__).resolve().parent
    script_path = shutil.which("tokensaver")
    script_dir = _script_dir()
    candidate_script = script_path or str(Path(script_dir) / "tokensaver")
    return {
        "name": "tokensaver",
        "version": __version__,
        "local_commit": local_commit(),
        "package_path": str(package_path),
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "python_prefix": sys.prefix,
        "base_prefix": sys.base_prefix,
        "in_venv": in_venv(),
        "install_mode": install_mode(package_path),
        "user_site": _safe_user_site(),
        "site_packages": sysconfig.get_paths().get("purelib"),
        "externally_managed_python": externally_managed_python(),
        "pip_command": f"{sys.executable} -m pip",
        "cli_script_path": candidate_script,
        "cli_script_on_path": script_path is not None,
        "cli_script_dir": str(Path(candidate_script).parent),
        "tokensaver_mcp_on_path": shutil.which("tokensaver-mcp") is not None,
        "project_dir": str(Path(project_dir).resolve()),
        "project_pins": scan_project_pins(project_dir),
    }


def doctor(
    *,
    project_dir: str | Path = ".",
    timeout: float = 1.0,
    check_remote: bool = True,
) -> dict[str, Any]:
    info = verbose_version_info(project_dir=project_dir)
    findings: list[Finding] = []

    if not _pip_available():
        findings.append(
            Finding(
                code="pip_unavailable",
                severity="high",
                message="Current Python cannot run pip.",
                evidence={"python_executable": sys.executable},
                recommendation="Install pip for this Python or use a virtual environment with pip available.",
            )
        )

    if info["externally_managed_python"] and not info["in_venv"]:
        findings.append(
            Finding(
                code="externally_managed_python",
                severity="medium",
                message="This Python appears to be externally managed.",
                evidence={"python_executable": sys.executable},
                recommendation="Prefer a project virtual environment; for temporary seed-user verification use --user --break-system-packages.",
            )
        )

    if not info["cli_script_on_path"]:
        findings.append(
            Finding(
                code="cli_script_not_on_path",
                severity="medium",
                message="The tokensaver console script is not on PATH.",
                evidence={"cli_script_dir": info["cli_script_dir"]},
                recommendation=f'Use "python3 -m tokensaver.cli ..." or add {info["cli_script_dir"]} to PATH.',
            )
        )

    current_commit = str(info.get("local_commit") or "")
    for pin in info["project_pins"]:
        pin_commit = str(pin.get("commit") or "")
        if current_commit and pin_commit and pin_commit != current_commit:
            findings.append(
                Finding(
                    code="project_pin_mismatch",
                    severity="high",
                    message="A project dependency file pins TokenSaver to a different commit.",
                    evidence={
                        "path": pin.get("path"),
                        "pinned_commit": pin_commit,
                        "local_commit": current_commit,
                    },
                    recommendation=f"Update {pin.get('path')} to pin TokenSaver at {current_commit}.",
                )
            )

    if not _trace_dir_writable(project_dir):
        findings.append(
            Finding(
                code="trace_dir_not_writable",
                severity="high",
                message=".tokensaver trace directory is not writable from this project directory.",
                evidence={"project_dir": str(Path(project_dir).resolve())},
                recommendation="Run from a writable project directory or configure a writable TokenSaver store_dir.",
            )
        )

    update = None
    if check_remote:
        update = check_for_update(timeout=timeout).to_dict()
        if update.get("status") == "cannot_check_remote":
            findings.append(
                Finding(
                    code="network_unavailable",
                    severity="low",
                    message="Remote update metadata could not be fetched.",
                    evidence={"reason": update.get("reason"), "error": update.get("error")},
                    recommendation="Local TokenSaver is runnable; retry check-update later or use --offline in intentionally offline environments.",
                )
            )

    runtime_health = LocalStore(Path(project_dir) / ".tokensaver").read_health()
    runtime_findings = diagnose_health(runtime_health)
    environment_findings = [{**item.to_dict(), "category": "environment"} for item in findings]
    combined_findings = [
        {**item, "category": "runtime"}
        for item in runtime_findings
    ] + environment_findings
    runtime_failed = runtime_health.get("status") == "failed" or any(
        item.get("severity") == "high" for item in runtime_findings
    )
    ok = not runtime_failed and not any(item.severity == "high" for item in findings)
    return {
        "ok": ok,
        "status": "failed" if runtime_failed else ("ok" if ok else "degraded"),
        "version": info,
        "update": update,
        "runtime": runtime_health,
        "deployment_acceptance": runtime_health.get("deployment_acceptance") or {},
        "findings": combined_findings,
        "upgrade_command": build_upgrade_command(commit=current_commit or None),
    }


def verify_install(
    *,
    expected_commit: str | None = None,
    expected_version: str | None = None,
    project_dir: str | Path = ".",
    check_project_files: bool = False,
) -> dict[str, Any]:
    info = verbose_version_info(project_dir=project_dir)
    findings: list[Finding] = []

    if expected_version and info["version"] != expected_version:
        findings.append(
            Finding(
                code="version_mismatch",
                severity="high",
                message="Installed TokenSaver version does not match the expected version.",
                evidence={"expected_version": expected_version, "actual_version": info["version"]},
                recommendation=f"Install TokenSaver {expected_version} in {sys.executable}.",
            )
        )

    actual_commit = str(info.get("local_commit") or "")
    if expected_commit and actual_commit and actual_commit != expected_commit:
        findings.append(
            Finding(
                code="commit_mismatch",
                severity="high",
                message="Installed TokenSaver commit does not match the expected commit.",
                evidence={"expected_commit": expected_commit, "actual_commit": actual_commit},
                recommendation=f"Install TokenSaver from commit {expected_commit}.",
            )
        )
    if expected_commit and not actual_commit:
        findings.append(
            Finding(
                code="unknown_local_commit",
                severity="medium",
                message="TokenSaver could not determine the local source commit.",
                evidence={"expected_commit": expected_commit},
                recommendation="Reinstall from a pinned commit or run verify-install from a Git checkout.",
            )
        )

    project_pins_match = True
    if check_project_files and expected_commit:
        for pin in info["project_pins"]:
            pin_commit = str(pin.get("commit") or "")
            if pin_commit and pin_commit != expected_commit:
                project_pins_match = False
                findings.append(
                    Finding(
                        code="project_pin_mismatch",
                        severity="high",
                        message="Project dependency pin does not match the expected commit.",
                        evidence={
                            "path": pin.get("path"),
                            "pinned_commit": pin_commit,
                            "expected_commit": expected_commit,
                        },
                        recommendation=f"Update {pin.get('path')} to pin TokenSaver at {expected_commit}.",
                    )
                )

    ok = not any(item.severity == "high" for item in findings)
    return {
        "ok": ok,
        "version": info["version"],
        "commit": actual_commit or None,
        "expected_version": expected_version,
        "expected_commit": expected_commit,
        "project_pins_match": project_pins_match,
        "python_executable": info["python_executable"],
        "install_mode": info["install_mode"],
        "project_pins": info["project_pins"],
        "findings": [item.to_dict() for item in findings],
    }


def build_upgrade_command(
    *,
    commit: str | None = None,
    prefer_pipx: bool = False,
) -> str:
    target = INSTALL_URL + (f"@{commit}" if commit else "")
    if prefer_pipx and shutil.which("pipx"):
        return f"pipx install --force {target}"
    if in_venv():
        return f"{sys.executable} -m pip install --upgrade --force-reinstall {target}"
    if externally_managed_python():
        return (
            f"{sys.executable} -m pip install --user --break-system-packages "
            f"--upgrade --force-reinstall {target}"
        )
    return f"{sys.executable} -m pip install --upgrade --force-reinstall {target}"


def run_self_update(*, commit: str | None = None) -> dict[str, Any]:
    command = build_upgrade_command(commit=commit)
    process = subprocess.run(
        command.split(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "ok": process.returncode == 0,
        "returncode": process.returncode,
        "command": command,
        "stdout": process.stdout,
        "stderr": process.stderr,
    }


def scan_project_pins(project_dir: str | Path = ".") -> list[dict[str, Any]]:
    root = Path(project_dir).resolve()
    paths = [
        root / "requirements.txt",
        root / "pyproject.toml",
        root / "poetry.lock",
        root / "uv.lock",
        root / "Pipfile.lock",
    ]
    pins: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for match in re.finditer(r"TokenSaver(?:\.git)?@([A-Za-z0-9._/-]+)", text, flags=re.IGNORECASE):
            pins.append(
                {
                    "path": str(path),
                    "commit": _clean_ref(match.group(1)),
                    "source": "git_url",
                }
            )
        if re.search(r'(?im)^\s*tokensaver\s*[=<>!~]', text):
            pins.append(
                {
                    "path": str(path),
                    "commit": None,
                    "source": "package_version",
                }
            )
    return pins


def fix_project_pins(
    *,
    commit: str,
    project_dir: str | Path = ".",
) -> dict[str, Any]:
    changed: list[str] = []
    root = Path(project_dir).resolve()
    paths = [
        root / "requirements.txt",
        root / "pyproject.toml",
    ]
    pattern = re.compile(
        r"(git\+https://github\.com/zhangtao-jayce/TokenSaver\.git@)([A-Za-z0-9._/-]+)",
        flags=re.IGNORECASE,
    )
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        updated = pattern.sub(rf"\g<1>{commit}", text)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed.append(str(path))
    return {
        "changed": changed,
        "commit": commit,
        "ok": bool(changed),
    }


def local_commit() -> str | None:
    metadata_commit = _metadata_commit()
    if metadata_commit:
        return metadata_commit
    package_dir = Path(__file__).resolve().parent
    for cwd in (package_dir, package_dir.parent):
        try:
            process = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=False,
            )
        except OSError:
            continue
        value = process.stdout.strip()
        if process.returncode == 0 and value:
            return value
    return None


def _metadata_commit() -> str | None:
    try:
        distribution = importlib.metadata.distribution("tokensaver")
    except importlib.metadata.PackageNotFoundError:
        return None
    for file in distribution.files or []:
        if str(file).endswith("direct_url.json"):
            try:
                text = (distribution.locate_file(file)).read_text(encoding="utf-8")
            except OSError:
                return None
            payload = json.loads(text)
            commit = ((payload.get("vcs_info") or {}).get("commit_id") or "").strip()
            return commit[:7] if commit else None
    return None


def in_venv() -> bool:
    return sys.prefix != sys.base_prefix


def externally_managed_python() -> bool:
    marker = Path(sysconfig.get_path("stdlib") or "") / "EXTERNALLY-MANAGED"
    return marker.exists()


def install_mode(package_path: Path) -> str:
    user_site = _safe_user_site()
    if in_venv():
        return "venv"
    if user_site and str(package_path).startswith(user_site):
        return "user-site"
    if externally_managed_python():
        return "externally-managed"
    return "system-or-local"


def _pip_available() -> bool:
    process = subprocess.run(
        [sys.executable, "-m", "pip", "--version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return process.returncode == 0


def _trace_dir_writable(project_dir: str | Path) -> bool:
    root = Path(project_dir).resolve() / ".tokensaver"
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def _script_dir() -> str:
    return sysconfig.get_path("scripts") or ""


def _safe_user_site() -> str:
    try:
        return site.getusersitepackages()
    except (AttributeError, RuntimeError):
        return ""


def _clean_ref(value: str) -> str:
    return value.strip().split()[0].strip("\"';,")


def to_pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)
