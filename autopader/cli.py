"""Command-line interface for the GenAR Version 0 pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analysis import compute_all
from .data.loader import load_dataset
from .data.normalizer import build_case_table, build_reaction_table
from .data.validator import validate
from .evidence.manifest import ReportManifest
from .pipeline import run_pipeline
from .report.assembler import ReportNotReadyError
from .review.review import load_review_state, save_review_state

DEFAULT_DATASET = "Bisoprolol_icsr_sample_1068rows.xlsx"
DEFAULT_OUTPUT = "report_output.md"
DEFAULT_REVIEW = "review_state.json"

SECTIONS = (
    "narrative_summary",
    "summary_analysis",
    "reaction_analysis",
    "serious_alerts",
    "trends",
    "history_of_actions",
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autopader",
        description="Evidence-grounded PADER-style report generator",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="run the full pipeline")
    gen.add_argument("--dataset", default=DEFAULT_DATASET)
    gen.add_argument("--output", default=DEFAULT_OUTPUT)
    gen.add_argument("--review", default=DEFAULT_REVIEW)
    gen.add_argument(
        "--skip-llm",
        action="store_true",
        help="use the deterministic EchoClient instead of the live LLM",
    )
    gen.add_argument(
        "--allow-pending",
        action="store_true",
        help="write a draft even though sections are not yet approved",
    )
    gen.set_defaults(func=_cmd_generate)

    rev = sub.add_parser("review", help="manage section review status")
    rev_sub = rev.add_subparsers(dest="review_command", required=True)
    flags = argparse.ArgumentParser(add_help=False)
    flags.add_argument("--note", default="")
    flags.add_argument("--text", default=None)
    flags.add_argument("--review", default=DEFAULT_REVIEW)
    for name in ("approve", "flag", "edit"):
        cmd = rev_sub.add_parser(name, parents=[flags], help=f"{name.title()} a section")
        cmd.add_argument("section", choices=list(SECTIONS) + ["analysis"])
    rev.set_defaults(func=_cmd_review)

    ana = sub.add_parser("analyze", help="print the deterministic analysis summary")
    ana.add_argument("--dataset", default=DEFAULT_DATASET)
    ana.set_defaults(func=_cmd_analyze)
    return parser


def _add_flag_subcommands(rev_sub, rev) -> None:
    """flag/edit subcommands attach the rest of rev's args already declared."""


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # argparse: --help or invalid args
        code = exc.code
        return int(code) if isinstance(code, int) else 0
    try:
        return int(args.func(args) or 0)
    except (ReportNotReadyError, RuntimeError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _cmd_generate(args) -> int:
    manifest: ReportManifest
    manifest, output = run_pipeline(
        dataset_path=args.dataset,
        output_path=args.output,
        review_path=args.review,
        skip_llm=args.skip_llm,
        allow_pending=args.allow_pending,
    )
    delim = "=" * 60
    print(delim)
    print(f"report written to: {output}")
    print(f"dataset sha256:   {manifest.dataset_sha256}")
    print(f"analysis version: {manifest.analysis_version}")
    print(f"model:            {manifest.model}")
    print(f"prompt version:   {manifest.prompt_version}")
    print(delim)
    print(
        "Review required before the report is final: "
        "`python -m autopader review approve <section> --note ...`"
    )
    return 0


def _cmd_analyze(args) -> int:
    df, dataset_sha256 = load_dataset(args.dataset)
    validation = validate(df)
    if validation.errors:
        print("validation errors:\n" + "\n".join(f"- {e}" for e in validation.errors))
        return 1
    case_table = build_case_table(df)
    reaction_df, _ = build_reaction_table(df)
    results = compute_all(case_table, reaction_df, dataset_sha256[:8])
    print(f"reporting period : {results.reporting_period[0]} .. {results.reporting_period[1]}")
    print(f"total cases      : {results.total_cases}")
    print(f"serious cases    : {results.serious_cases}")
    print(f"expedited cases  : {results.expedited_cases}")
    print("top reactions    : " + results.evidence["react.top_reactions"].value)
    for i, m in enumerate(results.monthly_cases):
        end = ", " if i < len(results.monthly_cases) - 1 else "\n"
        print(f"  {m['month']}: {m['count']} ({m['delta']:+d})", end=end)
    return 0


def _cmd_review(args) -> int:
    path = Path(args.review)
    state = load_review_state(path)
    command = args.review_command
    if command == "approve":
        state.set_status(args.section, "approved", note=args.note)
    elif command == "flag":
        state.set_status(args.section, "flagged", note=args.note or "flagged during review")
    elif command == "edit":
        if not args.text:
            print("error: --text is required for edit", file=sys.stderr)
            return 1
        state.set_status(args.section, "edited", note=args.note, edited_text=args.text)
    else:
        print(f"error: unknown review command '{command}'", file=sys.stderr)
        return 1
    save_review_state(state, path)
    print(f"review state updated: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
