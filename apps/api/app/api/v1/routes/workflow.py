import json
import logging
from collections.abc import AsyncGenerator
from typing import Annotated, Literal, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from langchain_core.runnables import RunnableConfig
from langgraph.graph import START
from langgraph.graph.state import CompiledStateGraph
from pydantic import Field

from app.core.errors import AppError
from app.dependencies.account_profile import get_account_profile_service
from app.dependencies.authentication import (
    AuthenticatedPrincipal,
    get_current_principal,
)
from app.dependencies.mentor_discovery import get_mentor_discovery_service
from app.dependencies.outreach import get_outreach_service
from app.schemas.base import ApiModel
from app.schemas.discovery import DiscoveryText
from app.services.account_profile import AccountProfileService
from app.services.mentor_discovery import MentorDiscoveryReader
from app.services.outreach import OutreachService
from app.services.workflow import require_workflow_owner
from app.workflow.graph import build_placement_graph
from app.workflow.state import PlacementWorkflowState

router = APIRouter(prefix="/workflow", tags=["workflow"])
logger = logging.getLogger(__name__)


class WorkflowStartRequest(ApiModel):
    query: DiscoveryText
    paper_limit: int = Field(default=20, ge=1, le=25)
    candidate_limit: int = Field(default=12, ge=1, le=20)
    generation_preference: Literal["auto", "deterministic"] = "auto"


class WorkflowResumeRequest(ApiModel):
    selected_mentor_id: UUID
    selected_paper_ids: list[UUID] = Field(min_length=1, max_length=2)


def get_workflow_graph(request: Request) -> CompiledStateGraph:  # type: ignore[type-arg]
    """Build and compile the workflow graph with the persistent checkpointer."""
    checkpointer = request.app.state.workflow_checkpointer
    if checkpointer is None:
        raise AppError(
            code="workflow_unavailable",
            message="Workflow storage is temporarily unavailable. Please try again.",
            status_code=503,
        )
    graph = build_placement_graph()
    return graph.compile(checkpointer=checkpointer)


@router.post("/start", summary="Start a new placement workflow")
async def start_workflow(
    request: WorkflowStartRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    profiles: Annotated[AccountProfileService, Depends(get_account_profile_service)],
    graph: Annotated[CompiledStateGraph, Depends(get_workflow_graph)],  # type: ignore[type-arg]
) -> dict[str, str]:
    """Initialize a workflow run and return the thread ID."""
    await profiles.get_profile()
    thread_id = str(uuid4())
    config = cast(RunnableConfig, {"configurable": {"thread_id": thread_id}})

    state: PlacementWorkflowState = {
        "query": request.query,
        "owner_id": str(principal.owner_id),
        "paper_limit": request.paper_limit,
        "candidate_limit": request.candidate_limit,
        "generation_preference": request.generation_preference,
    }

    await graph.aupdate_state(config, state, as_node=START)
    return {"thread_id": thread_id}


@router.post("/{thread_id}/resume", summary="Provide human input to resume drafting")
async def resume_workflow(
    thread_id: str,
    request: WorkflowResumeRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    graph: Annotated[CompiledStateGraph, Depends(get_workflow_graph)],  # type: ignore[type-arg]
) -> dict[str, str]:
    """Update workflow state with mentor selection, readying it for the next run."""
    await require_workflow_owner(graph, thread_id, principal.owner_id)
    config = cast(RunnableConfig, {"configurable": {"thread_id": thread_id}})

    state_update = {
        "selected_mentor_id": str(request.selected_mentor_id),
        "selected_paper_ids": [str(p) for p in request.selected_paper_ids],
    }

    await graph.aupdate_state(config, state_update, as_node="discover_mentors")
    return {"status": "resumed", "thread_id": thread_id}


@router.get("/{thread_id}/stream", summary="Stream workflow progress (SSE)")
async def stream_workflow(
    thread_id: str,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    graph: Annotated[CompiledStateGraph, Depends(get_workflow_graph)],  # type: ignore[type-arg]
    mentor_service: Annotated[
        MentorDiscoveryReader, Depends(get_mentor_discovery_service)
    ],
    outreach_service: Annotated[OutreachService, Depends(get_outreach_service)],
) -> StreamingResponse:
    """Execute the workflow and stream events via Server-Sent Events."""

    await require_workflow_owner(graph, thread_id, principal.owner_id)

    config = cast(
        RunnableConfig,
        {
            "configurable": {
                "thread_id": thread_id,
                "mentor_service": mentor_service,
                "outreach_service": outreach_service,
            }
        },
    )

    async def event_generator() -> AsyncGenerator[str]:
        try:
            async for event in graph.astream(
                None, config=config, stream_mode="updates"
            ):
                data = json.dumps(jsonable_encoder(event))
                yield f"data: {data}\n\n"
            yield "event: complete\ndata: {}\n\n"
        except Exception:
            logger.exception("Workflow execution failed")
            error_data = json.dumps(
                {"error": "The workflow could not complete. Please try again."}
            )
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
