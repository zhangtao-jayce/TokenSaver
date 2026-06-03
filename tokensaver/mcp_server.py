"""Dependency-free stdio JSON-RPC server exposing TokenSaver tools."""

from __future__ import annotations

import json
import sys
from typing import Any

from . import __version__
from .brief import generate_repair_brief
from .diagnosis import diagnose_run
from .install import build_upgrade_command, doctor, verbose_version_info, verify_install
from .planner import plan_task
from .runtime import record_agent_run
from .store import LocalStore
from .tokenizer import estimate_tokens
from .update import check_for_update


TOOLS = [
    {
        "name": "tokensaver.plan_task",
        "description": "Plan context and model strategy for an AI workflow task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_message": {"type": "string"},
                "model": {"type": "string"},
                "output_tokens_estimate": {"type": "integer"},
                "context_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "kind": {"type": "string"},
                            "content": {"type": "string"},
                        },
                    },
                },
                "preferred_mode": {"type": "string"},
                "max_context_tokens": {"type": "integer"},
            },
            "required": ["user_message"],
        },
    },
    {
        "name": "tokensaver.estimate_tokens",
        "description": "Estimate token count locally without an LLM call.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "tokensaver.record_agent_run",
        "description": "Record, diagnose, and store one Agent runtime trace locally.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run": {"type": "object"},
                "store_dir": {"type": "string"},
            },
            "required": ["run"],
        },
    },
    {
        "name": "tokensaver.get_latest_runs",
        "description": "Read latest locally stored Agent runs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer"},
                "store_dir": {"type": "string"},
            },
        },
    },
    {
        "name": "tokensaver.diagnose_roi",
        "description": "Diagnose an Agent run or the latest stored run using local ROI rules.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run": {"type": "object"},
                "store_dir": {"type": "string"},
            },
        },
    },
    {
        "name": "tokensaver.generate_repair_brief",
        "description": "Generate a Codex / Claude Code repair brief from a run or latest stored run.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run": {"type": "object"},
                "store_dir": {"type": "string"},
            },
        },
    },
    {
        "name": "tokensaver.get_version",
        "description": "Return TokenSaver version, Python path, package path, commit, and CLI path metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_dir": {"type": "string"},
                "verbose": {"type": "boolean"},
            },
        },
    },
    {
        "name": "tokensaver.check_update",
        "description": "Check whether a newer TokenSaver version is available from public GitHub metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "timeout": {"type": "number"},
                "offline": {"type": "boolean"},
            },
        },
    },
    {
        "name": "tokensaver.doctor",
        "description": "Diagnose TokenSaver installation, Python environment, PATH, remote metadata, and project pins.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_dir": {"type": "string"},
                "timeout": {"type": "number"},
                "offline": {"type": "boolean"},
            },
        },
    },
    {
        "name": "tokensaver.verify_install",
        "description": "Verify installed TokenSaver version, commit, and optional project dependency pins.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_dir": {"type": "string"},
                "commit": {"type": "string"},
                "version": {"type": "string"},
                "check_project_files": {"type": "boolean"},
            },
        },
    },
    {
        "name": "tokensaver.upgrade_command",
        "description": "Generate a copyable TokenSaver upgrade command for the current Python environment.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "commit": {"type": "string"},
                "pipx": {"type": "boolean"},
            },
        },
    },
]


def main() -> None:
    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            request = json.loads(raw_line)
            response = handle_request(request)
        except Exception as exc:  # Keep server alive after malformed requests.
            response = _error_response(None, -32603, str(exc))
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    method = request.get("method")
    request_id = request.get("id")
    params = request.get("params") or {}

    if method == "initialize":
        return _result_response(
            request_id,
            {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "tokensaver", "version": __version__},
                "capabilities": {"tools": {}},
            },
        )
    if method == "tools/list":
        return _result_response(request_id, {"tools": TOOLS})
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        return _result_response(request_id, _call_tool(name, arguments))
    if method == "ping":
        return _result_response(request_id, {})

    return _error_response(request_id, -32601, f"Unknown method: {method}")


def _call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "tokensaver.plan_task":
        plan = plan_task(
            user_message=arguments.get("user_message", ""),
            model=arguments.get("model"),
            output_tokens_estimate=int(arguments.get("output_tokens_estimate", 1_000)),
            context_items=arguments.get("context_items") or [],
            preferred_mode=arguments.get("preferred_mode", "suggest"),
            max_context_tokens=int(arguments.get("max_context_tokens", 12_000)),
        ).to_dict()
        return _tool_text(plan)

    if name == "tokensaver.estimate_tokens":
        result = {"tokens_estimate": estimate_tokens(arguments.get("text", ""))}
        return _tool_text(result)

    if name == "tokensaver.record_agent_run":
        result = record_agent_run(
            arguments.get("run") or {},
            store_dir=arguments.get("store_dir") or ".tokensaver",
        )
        return _tool_text(result)

    if name == "tokensaver.get_latest_runs":
        store = LocalStore(arguments.get("store_dir") or ".tokensaver")
        result = {"runs": store.load_runs(limit=int(arguments.get("limit", 20)))}
        return _tool_text(result)

    if name == "tokensaver.diagnose_roi":
        run = arguments.get("run") or _latest_run(arguments.get("store_dir") or ".tokensaver")
        if not run:
            return {"isError": True, "content": [{"type": "text", "text": "No run provided or stored."}]}
        return _tool_text(diagnose_run(run))

    if name == "tokensaver.generate_repair_brief":
        run = arguments.get("run") or _latest_run(arguments.get("store_dir") or ".tokensaver")
        if not run:
            return {"isError": True, "content": [{"type": "text", "text": "No run provided or stored."}]}
        diagnosed = dict(run)
        diagnosed["diagnosis"] = diagnose_run(diagnosed)
        return _tool_text({"brief": generate_repair_brief(diagnosed)})

    if name == "tokensaver.get_version":
        result = verbose_version_info(
            project_dir=arguments.get("project_dir") or "."
        )
        if not bool(arguments.get("verbose", True)):
            result = {
                "name": result["name"],
                "version": result["version"],
                "local_commit": result["local_commit"],
                "python_executable": result["python_executable"],
            }
        return _tool_text(result)

    if name == "tokensaver.check_update":
        if bool(arguments.get("offline")):
            result = {
                "status": "cannot_check_remote",
                "reason": "offline_mode",
                "local_installation_ok": True,
                "version": verbose_version_info(),
            }
        else:
            result = check_for_update(timeout=float(arguments.get("timeout", 2.0))).to_dict()
        return _tool_text(result)

    if name == "tokensaver.doctor":
        return _tool_text(
            doctor(
                project_dir=arguments.get("project_dir") or ".",
                timeout=float(arguments.get("timeout", 1.0)),
                check_remote=not bool(arguments.get("offline")),
            )
        )

    if name == "tokensaver.verify_install":
        return _tool_text(
            verify_install(
                expected_commit=arguments.get("commit"),
                expected_version=arguments.get("version"),
                project_dir=arguments.get("project_dir") or ".",
                check_project_files=bool(arguments.get("check_project_files")),
            )
        )

    if name == "tokensaver.upgrade_command":
        return _tool_text(
            {
                "command": build_upgrade_command(
                    commit=arguments.get("commit"),
                    prefer_pipx=bool(arguments.get("pipx")),
                )
            }
        )

    return {
        "isError": True,
        "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
    }


def _tool_text(value: Any) -> dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(value, ensure_ascii=False, indent=2),
            }
        ]
    }


def _latest_run(store_dir: str) -> dict[str, Any] | None:
    return LocalStore(store_dir).latest_run()


def _result_response(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error_response(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


if __name__ == "__main__":
    main()
