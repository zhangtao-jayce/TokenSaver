"""Command-line entrypoint for local TokenSaver utilities."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .brief import generate_repair_brief
from .diagnosis import diagnose_run
from .planner import plan_task
from .runtime import record_agent_run
from .store import LocalStore
from .tokenizer import estimate_tokens


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tokensaver")
    subparsers = parser.add_subparsers(dest="command", required=True)

    estimate_parser = subparsers.add_parser("estimate", help="Estimate tokens.")
    estimate_parser.add_argument("text", nargs="?", help="Text to estimate.")
    estimate_parser.add_argument("--file", help="Read text from file.")

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


if __name__ == "__main__":
    raise SystemExit(main())
