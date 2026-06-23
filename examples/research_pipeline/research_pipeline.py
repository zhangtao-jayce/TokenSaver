"""Offline batch/research pipeline example with an external Agent handoff."""

from __future__ import annotations

import argparse
from pathlib import Path

from tokensaver import TokenSaver
from tokensaver.profile import template_profile


def run_pipeline(*, store_dir: Path, output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "raw.md"
    task_path = output_dir / "filter_task.md"
    processed_path = output_dir / "processed.md"

    profile = template_profile("research-agent")
    profile["budgets"]["daily_research"] = {
        "input_tokens": 20_000,
        "output_tokens": 2_000,
        "latency_ms": 120_000,
    }
    tokensaver = TokenSaver(
        app="research_pipeline",
        channel="cli",
        store_dir=store_dir,
        profile=profile,
    )

    with tokensaver.run(
        user_message="Build the daily research digest.",
        task_type="daily_research",
        route="batch_pipeline",
        metadata={"environment": "example", "output_dir": str(output_dir)},
    ) as run:
        rss_items = ["Release notes", "Integration guide", "Benchmark update"]
        run.record_tool_call(
            "rss_fetch",
            input_text="offline fixture",
            output_text="\n".join(rss_items),
            latency_ms=5,
            metadata={"source_count": 1, "item_count": len(rss_items)},
        )
        selected = list(dict.fromkeys(rss_items))
        run.record_tool_call(
            "dedupe_select",
            input_text="\n".join(rss_items),
            output_text="\n".join(selected),
            latency_ms=1,
            metadata={"selected_count": len(selected)},
        )

        raw_path.write_text("\n".join(f"- {item}" for item in selected) + "\n", encoding="utf-8")
        task_path.write_text(
            "Analyze raw.md and write the final digest to processed.md.\n",
            encoding="utf-8",
        )
        run.add_handoff(
            agent="codex",
            input_artifacts=[str(raw_path), str(task_path)],
            instruction="Analyze the selected research items and preserve source attribution.",
            expected_output=str(processed_path),
            status="prepared",
            metadata={"selected_count": len(selected)},
        )
        run.add_quality_signal("raw_output_generated", raw_path.exists())
        run.add_quality_signal("filter_task_generated", task_path.exists())
        run.add_quality_signal("handoff_complete", True)
        run.record_final_answer(f"Prepared {len(selected)} items for external Agent analysis.")

    return run.result or {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store-dir", type=Path, default=Path(".tokensaver"))
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    args = parser.parse_args()
    result = run_pipeline(store_dir=args.store_dir, output_dir=args.output_dir)
    print(result["artifacts"]["report_path"])


if __name__ == "__main__":
    main()
