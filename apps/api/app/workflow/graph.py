"""LangGraph nodes and graph construction for the placement journey."""

import logging
from typing import Any
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from app.core.errors import AppError
from app.schemas.mentor_discovery import MentorDiscoveryRequest
from app.schemas.outreach import OutreachDraftCreateRequest
from app.services.mentor_discovery import MentorDiscoveryService
from app.services.outreach import OutreachService
from app.workflow.state import PlacementWorkflowState

logger = logging.getLogger(__name__)


async def discover_mentors(
    state: PlacementWorkflowState, config: RunnableConfig
) -> dict[str, Any]:
    """Retrieve papers and derive ranked mentor candidates deterministically."""
    logger.info("Executing node: discover_mentors")
    mentor_service: MentorDiscoveryService = config["configurable"]["mentor_service"]

    try:
        request = MentorDiscoveryRequest(
            query=state["query"],
            paper_limit=state.get("paper_limit", 20),
            candidate_limit=state.get("candidate_limit", 12),
        )
        response = await mentor_service.search(request)
        return {"discovery_response": response.model_dump(mode="json")}
    except AppError as e:
        return {"discovery_error": e.message}
    except Exception:
        logger.exception("Unexpected error in discover_mentors")
        return {"discovery_error": "An unexpected error occurred during discovery."}


def require_selection(state: PlacementWorkflowState) -> str:
    """Routing edge to determine if human input is ready for drafting."""
    if not state.get("selected_mentor_id") or not state.get("selected_paper_ids"):
        return "wait_for_selection"
    return "generate_draft"


async def generate_draft(
    state: PlacementWorkflowState, config: RunnableConfig
) -> dict[str, Any]:
    """Generate an evidence-grounded outreach draft based on human selection."""
    logger.info("Executing node: generate_draft")
    outreach_service: OutreachService = config["configurable"]["outreach_service"]

    mentor_id_str = state.get("selected_mentor_id")
    paper_ids_str = state.get("selected_paper_ids")
    if not mentor_id_str or not paper_ids_str:
        return {"draft_error": "Missing selection for drafting."}

    try:
        request = OutreachDraftCreateRequest(
            query=state["query"],
            mentor_id=UUID(mentor_id_str),
            paper_ids=[UUID(p) for p in paper_ids_str],
            generation_preference=state.get("generation_preference", "auto"),
        )
        response = await outreach_service.create(request)
        return {"draft_response": response.model_dump(mode="json")}
    except AppError as e:
        return {"draft_error": e.message}
    except Exception:
        logger.exception("Unexpected error in generate_draft")
        return {"draft_error": "An unexpected error occurred during draft generation."}


def build_placement_graph() -> StateGraph:  # type: ignore[type-arg]
    """Build the LangGraph state machine with deterministic nodes and pauses."""

    workflow = StateGraph(PlacementWorkflowState)

    # Add nodes
    workflow.add_node("discover_mentors", discover_mentors)
    workflow.add_node("generate_draft", generate_draft)

    # Set entry point
    workflow.set_entry_point("discover_mentors")

    # After discovery, we wait for human input. We can use an interrupt or simply end
    # the turn and have the client resume at a specific edge. Using `interrupt` is
    # preferred in newer LangGraph. But for a simpler flow, we can just define an edge
    # that points to END or the next step based on state.

    # We add a conditional edge from discover_mentors to END, pausing.
    # The client will submit state updates (selected_mentor_id, selected_paper_ids)
    # and then the graph continues. Actually, standard way is to interrupt.

    # Let's route from discover_mentors to END. The user will call the graph again
    # starting from a different node, OR we use `interrupt()`. Let's use the explicit
    # conditional edge. We will always pause after discovery.

    def after_discovery(state: PlacementWorkflowState) -> str:
        if state.get("selected_mentor_id") and state.get("selected_paper_ids"):
            return "generate_draft"
        return END

    workflow.add_conditional_edges("discover_mentors", after_discovery)

    # Draft is the end of this workflow
    workflow.add_edge("generate_draft", END)

    return workflow
