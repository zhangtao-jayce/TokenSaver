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


if __name__ == "__main__":
    raise SystemExit(main())
