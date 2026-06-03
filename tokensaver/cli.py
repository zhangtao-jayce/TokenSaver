"""Command-line entrypoint for local TokenSaver utilities."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .brief import generate_repair_brief
from .diagnosis import diagnose_run
from .install import (
    build_upgrade_command,
    doctor,
    fix_project_pins,
    run_self_update,
    verbose_version_info,
    verify_install,
)
from .planner import plan_task
from .runtime import record_agent_run
from .store import LocalStore
from .tokenizer import estimate_tokens
from .update import check_for_update, get_version_info


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tokensaver")
    subparsers = parser.add_subparsers(dest="command", required=True)

    estimate_parser = subparsers.add_parser("estimate", help="Estimate tokens.")
    estimate_parser.add_argument("text", nargs="?", help="Text to estimate.")
    estimate_parser.add_argument("--file", help="Read text from file.")

    version_parser = subparsers.add_parser("version", help="Show local TokenSaver version.")
    version_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    version_parser.add_argument("--verbose", action="store_true", help="Show Python, package, commit, and CLI path details.")
    version_parser.add_argument("--project-dir", default=".")

    update_parser = subparsers.add_parser("check-update", help="Check whether TokenSaver has a newer version.")
    update_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    update_parser.add_argument("--timeout", type=float, default=3.0)
    update_parser.add_argument("--offline", action="store_true", help="Do not query remote metadata.")

    doctor_parser = subparsers.add_parser("doctor", help="Diagnose TokenSaver installation and project pins.")
    doctor_parser.add_argument("--json", action="store_true")
    doctor_parser.add_argument("--project-dir", default=".")
    doctor_parser.add_argument("--timeout", type=float, default=1.0)
    doctor_parser.add_argument("--offline", action="store_true")
    doctor_parser.add_argument("--fix-requirements", action="store_true", help="Update TokenSaver git pins in requirements.txt/pyproject.toml to the local commit.")

    verify_parser = subparsers.add_parser("verify-install", help="Verify installed TokenSaver version and commit.")
    verify_parser.add_argument("--json", action="store_true")
    verify_parser.add_argument("--commit")
    verify_parser.add_argument("--version")
    verify_parser.add_argument("--project-dir", default=".")
    verify_parser.add_argument("--check-project-files", action="store_true")
    verify_parser.add_argument("--check-mcp", action="store_true")

    upgrade_command_parser = subparsers.add_parser("upgrade-command", help="Generate an upgrade command for this Python environment.")
    upgrade_command_parser.add_argument("--json", action="store_true")
    upgrade_command_parser.add_argument("--commit")
    upgrade_command_parser.add_argument("--pipx", action="store_true", help="Prefer pipx command when pipx is available.")

    self_update_parser = subparsers.add_parser("self-update", help="Print or execute a TokenSaver self-update command.")
    self_update_parser.add_argument("--json", action="store_true")
    self_update_parser.add_argument("--commit")
    self_update_parser.add_argument("--execute", action="store_true", help="Actually run pip to update TokenSaver.")

    plan_parser = subparsers.add_parser("plan", help="Plan a task.")
    plan_parser.add_argument("message", nargs="?", help="User task message.")
    plan_parser.add_argument("--message-file", help="Read user message from file.")
    plan_parser.add_argument("--model", help="Model id for cost estimation.")
    plan_parser.add_argument(
        "--context",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="Add context item from a file. Can be passed multiple times.",
    )
    plan_parser.add_argument("--preferred-mode", default="suggest")
    plan_parser.add_argument("--max-context-tokens", type=int, default=12_000)

    record_parser = subparsers.add_parser("record-run", help="Record and diagnose an Agent run.")
    record_parser.add_argument("--file", help="Read run JSON from file. Defaults to stdin.")
    record_parser.add_argument("--store-dir", default=".tokensaver")

    latest_parser = subparsers.add_parser("latest", help="Read latest TokenSaver result.")
    latest_parser.add_argument(
        "--kind",
        choices=["run", "summary", "brief", "panel"],
        default="summary",
        help="Which latest artifact to print.",
    )
    latest_parser.add_argument("--store-dir", default=".tokensaver")

    diagnose_parser = subparsers.add_parser("diagnose-run", help="Diagnose a run JSON.")
    diagnose_parser.add_argument("--file", help="Read run JSON from file. Defaults to stdin.")

    brief_parser = subparsers.add_parser("repair-brief", help="Generate a repair brief from run JSON.")
    brief_parser.add_argument("--file", help="Read run JSON from file. Defaults to stdin.")

    list_parser = subparsers.add_parser("list", help="List recent TokenSaver runs.")
    list_parser.add_argument("--store-dir", default=".tokensaver")
    list_parser.add_argument("--limit", type=int, default=20)
    list_parser.add_argument("--app")
    list_parser.add_argument("--channel")
    list_parser.add_argument("--task-type")
    list_parser.add_argument("--route")

    show_parser = subparsers.add_parser("show", help="Show a recorded run by id or latest.")
    show_parser.add_argument("run_id", nargs="?", default="latest")
    show_parser.add_argument("--store-dir", default=".tokensaver")

    report_parser = subparsers.add_parser("report", help="Print a run summary.")
    report_parser.add_argument("run_id", nargs="?", default="latest")
    report_parser.add_argument("--store-dir", default=".tokensaver")

    brief_latest_parser = subparsers.add_parser("brief", help="Print a repair brief for latest or a run id.")
    brief_latest_parser.add_argument("run_id", nargs="?", default="latest")
    brief_latest_parser.add_argument("--store-dir", default=".tokensaver")

    compare_parser = subparsers.add_parser("compare", help="Compare two recorded runs.")
    compare_parser.add_argument("--before", required=True)
    compare_parser.add_argument("--after", required=True)
    compare_parser.add_argument("--store-dir", default=".tokensaver")

    top_tools_parser = subparsers.add_parser("top-tools", help="Show expensive tools from recent runs.")
    top_tools_parser.add_argument("--store-dir", default=".tokensaver")
    top_tools_parser.add_argument("--last", type=int, default=50)

    args = parser.parse_args(argv)

    if args.command == "estimate":
        text = _read_arg_text(args.text, args.file)
        print(json.dumps({"tokens_estimate": estimate_tokens(text)}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "version":
        info = verbose_version_info(project_dir=args.project_dir) if args.verbose else get_version_info()
        if args.json:
            print(json.dumps(info, ensure_ascii=False, indent=2))
        elif args.verbose:
            _print_verbose_version(info)
        else:
            print(f"TokenSaver {info['version']}")
            print(info["repository"])
        return 0

    if args.command == "check-update":
        if args.offline:
            local = verbose_version_info()
            data = {
                "local_version": local["version"],
                "local_commit": local["local_commit"],
                "latest_version": None,
                "latest_commit": None,
                "status": "cannot_check_remote",
                "reason": "offline_mode",
                "local_installation_ok": True,
                "upgrade_command": build_upgrade_command(),
                "compatibility": [
                    "Existing local traces remain readable.",
                    "Offline mode skips remote metadata checks.",
                ],
                "error": "",
            }
        else:
            info = check_for_update(timeout=args.timeout)
            data = info.to_dict()
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            _print_update_info(data)
        return 0

    if args.command == "doctor":
        result = doctor(
            project_dir=args.project_dir,
            timeout=args.timeout,
            check_remote=not args.offline,
        )
        if args.fix_requirements:
            commit = ((result.get("version") or {}).get("local_commit") if isinstance(result.get("version"), dict) else None)
            if not commit:
                raise SystemExit("Cannot fix requirements because local TokenSaver commit is unknown.")
            result["fix_requirements"] = fix_project_pins(
                commit=str(commit),
                project_dir=args.project_dir,
            )
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            _print_doctor(result)
        return 0 if result.get("ok") else 1

    if args.command == "verify-install":
        result = verify_install(
            expected_commit=args.commit,
            expected_version=args.version,
            project_dir=args.project_dir,
            check_project_files=args.check_project_files,
        )
        if args.check_mcp:
            result["tokensaver_mcp_on_path"] = verbose_version_info(
                project_dir=args.project_dir
            )["tokensaver_mcp_on_path"]
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            _print_verify(result)
        return 0 if result.get("ok") else 1

    if args.command == "upgrade-command":
        command = build_upgrade_command(commit=args.commit, prefer_pipx=args.pipx)
        result = {"command": command, "commit": args.commit}
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(command)
        return 0

    if args.command == "self-update":
        command = build_upgrade_command(commit=args.commit)
        if not args.execute:
            result = {
                "executed": False,
                "command": command,
                "next_step": "Re-run with --execute to perform the update.",
            }
        else:
            result = run_self_update(commit=args.commit)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.execute:
            print(f"Command: {result['command']}")
            print(f"Status: {'ok' if result['ok'] else 'failed'}")
            if result.get("stderr"):
                print(result["stderr"])
        else:
            print(command)
            print("Re-run with --execute to perform the update.")
        return 0 if result.get("ok", True) else 1

    if args.command == "plan":
        message = _read_arg_text(args.message, args.message_file)
        context_items = [_parse_context_arg(spec) for spec in args.context]
        plan = plan_task(
            user_message=message,
            model=args.model,
            context_items=context_items,
            preferred_mode=args.preferred_mode,
            max_context_tokens=args.max_context_tokens,
        )
        print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "record-run":
        run = _read_json_arg(args.file)
        recorded = record_agent_run(run, store_dir=args.store_dir)
        print(json.dumps(recorded, ensure_ascii=False, indent=2))
        return 0

    if args.command == "latest":
        store = LocalStore(args.store_dir)
        if args.kind == "run":
            print(json.dumps(store.latest_run() or {}, ensure_ascii=False, indent=2))
            return 0
        if args.kind == "brief":
            print(store.read_latest_brief(), end="")
            return 0
        if args.kind == "panel":
            print(str(store.panel_dir / "index.html"))
            return 0
        print(store.read_latest_report(), end="")
        return 0

    if args.command == "diagnose-run":
        run = _read_json_arg(args.file)
        print(json.dumps(diagnose_run(run), ensure_ascii=False, indent=2))
        return 0

    if args.command == "repair-brief":
        run = _read_json_arg(args.file)
        diagnosed = dict(run)
        diagnosed["diagnosis"] = diagnose_run(diagnosed)
        print(generate_repair_brief(diagnosed), end="")
        return 0

    if args.command == "list":
        store = LocalStore(args.store_dir)
        runs = _filter_runs(
            store.load_runs(limit=args.limit),
            app=args.app,
            channel=args.channel,
            task_type=args.task_type,
            route=args.route,
        )
        print(json.dumps([_run_list_item(run) for run in runs], ensure_ascii=False, indent=2))
        return 0

    if args.command == "show":
        run = _get_stored_run(args.store_dir, args.run_id)
        print(json.dumps(run or {}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "report":
        run = _get_stored_run(args.store_dir, args.run_id)
        if not run:
            raise SystemExit(f"Run not found: {args.run_id}")
        from .brief import generate_run_summary

        print(generate_run_summary(run), end="")
        return 0

    if args.command == "brief":
        run = _get_stored_run(args.store_dir, args.run_id)
        if not run:
            raise SystemExit(f"Run not found: {args.run_id}")
        print(generate_repair_brief(run), end="")
        return 0

    if args.command == "compare":
        store = LocalStore(args.store_dir)
        result = store.compare_runs(args.before, args.after)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "top-tools":
        store = LocalStore(args.store_dir)
        print(json.dumps(_top_tools(store.load_runs(limit=args.last)), ensure_ascii=False, indent=2))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


def _read_arg_text(value: str | None, path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8")
    if value:
        return value
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def _parse_context_arg(spec: str) -> dict[str, str]:
    if "=" not in spec:
        raise SystemExit(f"Invalid --context value {spec!r}; expected NAME=PATH")
    name, path = spec.split("=", 1)
    content = Path(path).read_text(encoding="utf-8")
    return {"name": name, "kind": "file", "content": content}


def _read_json_arg(path: str | None) -> dict[str, object]:
    text = Path(path).read_text(encoding="utf-8") if path else sys.stdin.read()
    if not text.strip():
        raise SystemExit("Expected run JSON from --file or stdin.")
    value = json.loads(text)
    if not isinstance(value, dict):
        raise SystemExit("Expected a JSON object.")
    return value


def _filter_runs(
    runs: list[dict[str, object]],
    *,
    app: str | None,
    channel: str | None,
    task_type: str | None,
    route: str | None,
) -> list[dict[str, object]]:
    filtered = []
    for run in runs:
        if app and run.get("app") != app:
            continue
        if channel and run.get("channel") != channel:
            continue
        if task_type and run.get("task_type") != task_type:
            continue
        if route and run.get("route") != route:
            continue
        filtered.append(run)
    return filtered


def _run_list_item(run: dict[str, object]) -> dict[str, object]:
    diagnosis = run.get("diagnosis") or {}
    if not isinstance(diagnosis, dict):
        diagnosis = {}
    return {
        "run_id": run.get("run_id"),
        "app": run.get("app"),
        "channel": run.get("channel"),
        "task_type": run.get("task_type"),
        "route": run.get("route"),
        "input_tokens": run.get("input_tokens", 0),
        "output_tokens": run.get("output_tokens", 0),
        "latency_ms": run.get("latency_ms", 0),
        "roi_score": diagnosis.get("roi_score", 100),
        "finding_codes": diagnosis.get("finding_codes", []),
    }


def _get_stored_run(store_dir: str, run_id: str) -> dict[str, object] | None:
    store = LocalStore(store_dir)
    if run_id == "latest":
        return store.latest_run()
    return store.find_run(run_id)


def _top_tools(runs: list[dict[str, object]]) -> list[dict[str, object]]:
    totals: dict[str, dict[str, object]] = {}
    for run in runs:
        for call in run.get("tool_calls") or []:
            if not isinstance(call, dict):
                continue
            name = str(call.get("name") or "unnamed")
            item = totals.setdefault(
                name,
                {"tool": name, "calls": 0, "input_tokens": 0, "output_tokens": 0},
            )
            item["calls"] = int(item["calls"]) + 1
            item["input_tokens"] = int(item["input_tokens"]) + int(call.get("input_tokens") or 0)
            item["output_tokens"] = int(item["output_tokens"]) + int(call.get("output_tokens") or 0)
    return sorted(totals.values(), key=lambda item: int(item["output_tokens"]), reverse=True)


def _print_update_info(data: dict[str, object]) -> None:
    print(f"TokenSaver local: {data.get('local_version')}")
    print(f"Local commit: {data.get('local_commit') or 'unknown'}")
    print(f"TokenSaver latest: {data.get('latest_version') or 'unknown'}")
    print(f"Status: {data.get('status')}")
    if data.get("reason"):
        print(f"Reason: {data.get('reason')}")
    if data.get("latest_commit"):
        print(f"Latest commit: {data.get('latest_commit')}")
    if data.get("error"):
        print(f"Error: {data.get('error')}")
    if data.get("status") == "cannot_check_remote":
        print("")
        print("Local TokenSaver is installed and runnable.")
        print("Remote update metadata could not be fetched.")
        print("Retry: python3 -m tokensaver.cli check-update")
    print("")
    print("Upgrade:")
    print(str(data.get("upgrade_command") or ""))
    compatibility = data.get("compatibility") or []
    if compatibility:
        print("")
        print("Compatibility:")
        for note in compatibility:
            print(f"- {note}")


def _print_verbose_version(info: dict[str, object]) -> None:
    print(f"TokenSaver {info.get('version')}")
    print(f"Local commit: {info.get('local_commit') or 'unknown'}")
    print(f"Package path: {info.get('package_path')}")
    print(f"Python: {info.get('python_executable')}")
    print(f"Python version: {info.get('python_version')}")
    print(f"Install mode: {info.get('install_mode')}")
    print(f"In venv: {info.get('in_venv')}")
    print(f"Externally managed Python: {info.get('externally_managed_python')}")
    print(f"CLI script path: {info.get('cli_script_path')}")
    print(f"CLI script on PATH: {info.get('cli_script_on_path')}")
    print(f"tokensaver-mcp on PATH: {info.get('tokensaver_mcp_on_path')}")


def _print_doctor(result: dict[str, object]) -> None:
    version = result.get("version") or {}
    if isinstance(version, dict):
        print(f"TokenSaver {version.get('version')} ({version.get('local_commit') or 'unknown commit'})")
        print(f"Python: {version.get('python_executable')}")
        print(f"Package: {version.get('package_path')}")
    print(f"Status: {'ok' if result.get('ok') else 'needs_attention'}")
    findings = result.get("findings") or []
    if findings:
        print("")
        print("Findings:")
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            print(f"- [{finding.get('severity')}] {finding.get('code')}: {finding.get('message')}")
            print(f"  Fix: {finding.get('recommendation')}")
    if result.get("fix_requirements"):
        fix = result["fix_requirements"]
        if isinstance(fix, dict):
            print("")
            print("Fixed dependency files:")
            for path in fix.get("changed") or []:
                print(f"- {path}")
    print("")
    print("Upgrade command:")
    print(result.get("upgrade_command") or "")


def _print_verify(result: dict[str, object]) -> None:
    print("Install verified." if result.get("ok") else "Install verification failed.")
    print("")
    print("TokenSaver:")
    print(f"  version: {result.get('version')}")
    print(f"  commit: {result.get('commit') or 'unknown'}")
    if result.get("expected_version"):
        print(f"  expected_version: {result.get('expected_version')}")
    if result.get("expected_commit"):
        print(f"  expected_commit: {result.get('expected_commit')}")
    print("")
    print("Python:")
    print(f"  executable: {result.get('python_executable')}")
    print(f"  install_mode: {result.get('install_mode')}")
    findings = result.get("findings") or []
    if findings:
        print("")
        print("Findings:")
        for finding in findings:
            if isinstance(finding, dict):
                print(f"- {finding.get('code')}: {finding.get('message')}")


if __name__ == "__main__":
    raise SystemExit(main())
