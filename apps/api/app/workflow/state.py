"""LangGraph typed state for the evidence-first placement journey."""

from typing import Any

from typing_extensions import TypedDict


class PlacementWorkflowState(TypedDict, total=False):
    """The workflow state for discovering and reaching out to a mentor.

    Keys are added or mutated as nodes execute, pausing at human checkpoints.
    """

    # Initialization inputs
    query: str
    owner_id: str  # Kept as string for JSON serialization
    paper_limit: int
    candidate_limit: int
    generation_preference: str

    # Node: discover_mentors output
    discovery_error: str | None
    discovery_response: dict[str, Any] | None

    # Checkpoint 1: Human selection inputs
    selected_mentor_id: str | None
    selected_paper_ids: list[str] | None

    # Node: generate_draft output
    draft_error: str | None
    draft_response: dict[str, Any] | None
