"""End-to-end pipeline tests (EchoClient path)."""

from __future__ import annotations

import pytest

from autopader.data.loader import LoadError
from autopader.evidence.manifest import ReportManifest
from autopader.llm.client import EchoClient
from autopader.pipeline import run_pipeline
from autopader.report.assembler import ReportNotReadyError


@pytest.fixture
def echo_factory():
    def _factory(packet):
        return EchoClient(packet)

    return _factory


def test_pipeline_happy_path(tmp_path, real_dataset_path, echo_factory) -> None:
    output = tmp_path / "report.md"
    review = tmp_path / "review.json"
    manifest, written = run_pipeline(
        dataset_path=real_dataset_path,
        output_path=output,
        review_path=review,
        client_factory=echo_factory,
        allow_pending=True,
    )
    assert isinstance(manifest, ReportManifest)
    assert written == output
    assert output.is_file()
    text = output.read_text(encoding="utf-8")
    assert "PADER-style Periodic Report" in text
    assert "Narrative Summary and Analysis" in text
    assert "Case Index" in text
    assert "Appendix — Traceability" in text
    assert manifest.dataset_sha256.startswith("21ef62fa")


def test_pipeline_writes_review_state(tmp_path, real_dataset_path, echo_factory) -> None:
    review = tmp_path / "review.json"
    run_pipeline(
        dataset_path=real_dataset_path,
        output_path=tmp_path / "report.md",
        review_path=review,
        client_factory=echo_factory,
        allow_pending=True,
    )
    assert review.is_file()
    assert "narrative_summary" in review.read_text(encoding="utf-8")


def test_pipeline_blocks_unapproved(tmp_path, real_dataset_path, echo_factory) -> None:
    with pytest.raises(ReportNotReadyError):
        run_pipeline(
            dataset_path=real_dataset_path,
            output_path=tmp_path / "report.md",
            review_path=tmp_path / "review.json",
            client_factory=echo_factory,
            allow_pending=False,
        )


def test_pipeline_rejects_invalid_dataset(tmp_path, echo_factory) -> None:
    bad = tmp_path / "bad.xlsx"
    bad.write_bytes(b"not an excel file")
    with pytest.raises(LoadError):
        run_pipeline(
            dataset_path=bad,
            output_path=tmp_path / "report.md",
            review_path=tmp_path / "review.json",
            client_factory=echo_factory,
            allow_pending=True,
        )


def test_pipeline_missing_dataset(tmp_path, echo_factory) -> None:
    with pytest.raises(LoadError):
        run_pipeline(
            dataset_path=tmp_path / "nope.xlsx",
            output_path=tmp_path / "report.md",
            review_path=tmp_path / "review.json",
            client_factory=echo_factory,
            allow_pending=True,
        )
