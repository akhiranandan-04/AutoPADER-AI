"""Human review: persistent per-section review state.

A section may only enter the final report when its status is ``approved`` or
``edited``. ``edited`` uses the reviewer's text verbatim, marked in the report.
Both generated sections and the deterministic analysis snapshot can be reviewed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

ReviewStatus = Literal["pending", "approved", "flagged", "edited", "analysis_approved"]


class SectionReview(BaseModel):
    section: str
    status: ReviewStatus = "pending"
    reviewer_notes: str = ""
    edited_text: str | None = Field(
        default=None, description="takes precedence over generated text when present"
    )


class ReviewState(BaseModel):
    reviews: dict[str, SectionReview] = Field(default_factory=dict)

    def get(self, section: str) -> SectionReview:
        if section not in self.reviews:
            self.reviews[section] = SectionReview(section=section)
        return self.reviews[section]

    def set_status(
        self,
        section: str,
        status: ReviewStatus,
        note: str = "",
        edited_text: str | None = None,
    ) -> SectionReview:
        review = self.get(section)
        review.status = status
        if note:
            review.reviewer_notes = note
        if edited_text is not None:
            review.edited_text = edited_text
        return review


def load_review_state(path: Path) -> ReviewState:
    if path.is_file():
        return ReviewState.model_validate(json.loads(path.read_text(encoding="utf-8")))
    return ReviewState()


def save_review_state(state: ReviewState, path: Path) -> None:
    path.write_text(state.model_dump_json(indent=2), encoding="utf-8")


def can_finalize(status: ReviewStatus) -> bool:
    return status in {"approved", "edited"}
