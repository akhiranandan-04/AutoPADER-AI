"""CLI tests for review/analyze flow."""

from __future__ import annotations

import json

from autopader.cli import main


def _run(args, capsys):
    code = main(args)
    captured = capsys.readouterr()
    return code, captured.out + captured.err


def test_analyze_prints_golden_numbers(real_dataset_path, capsys) -> None:
    code, out = _run(["analyze", "--dataset", str(real_dataset_path)], capsys)
    assert code == 0
    assert "total cases      : 1024" in out
    assert "serious cases    : 1023" in out


def test_analyze_missing_dataset(capsys) -> None:
    code, out = _run(["analyze", "--dataset", "does-not-exist.xlsx"], capsys)
    assert code == 1
    assert "error:" in out


def test_review_approve_roundtrip(tmp_path, capsys) -> None:
    review = tmp_path / "rv.json"
    code, _ = _run(
        ["review", "approve", "narrative_summary", "--note", "ok", "--review", str(review)],
        capsys,
    )
    assert code == 0
    state = json.loads(review.read_text(encoding="utf-8"))
    assert state["reviews"]["narrative_summary"]["status"] == "approved"


def test_review_edit_sets_text(tmp_path, capsys) -> None:
    review = tmp_path / "rv.json"
    code, _ = _run(
        [
            "review",
            "edit",
            "trends",
            "--text",
            "Custom text.",
            "--review",
            str(review),
        ],
        capsys,
    )
    assert code == 0
    state = json.loads(review.read_text(encoding="utf-8"))
    assert state["reviews"]["trends"]["status"] == "edited"
    assert state["reviews"]["trends"]["edited_text"] == "Custom text."


def test_review_flag_requires_no_text(tmp_path, capsys) -> None:
    review = tmp_path / "rv.json"
    code, _ = _run(["review", "flag", "trends", "--review", str(review)], capsys)
    assert code == 0
    state = json.loads(review.read_text(encoding="utf-8"))
    assert state["reviews"]["trends"]["status"] == "flagged"


def test_review_edit_missing_text(tmp_path, capsys) -> None:
    review = tmp_path / "rv.json"
    code, out = _run(["review", "edit", "trends", "--review", str(review)], capsys)
    assert code == 1
    assert "--text is required" in out


def test_review_bad_section(tmp_path, capsys) -> None:
    review = tmp_path / "rv.json"
    code, _ = _run(["review", "approve", "bogus", "--review", str(review)], capsys)
    assert code != 0


def test_no_command(capsys) -> None:
    code, _ = _run([], capsys)
    assert code == 2  # argparse requires a subcommand
