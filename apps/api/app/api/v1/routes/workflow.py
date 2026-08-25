import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Annotated, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph

from app.core.config import Settings
from app.dependencies.authentication import (
    AuthenticatedPrincipal,
    get_current_principal,
)
from app.dependencies.discovery import get_paper_discovery_service
from app.dependencies.outreach import get_outreach_service
from app.dependencies.profile import get_profile_service
from app.relevance.mentor import RelevanceWeights
from app.schemas.base import ApiModel
from app.schemas.discovery import DiscoveryText
from app.services.discovery import PaperDiscoveryReader
from app.services.mentor_discovery import MentorDiscoveryService
from app.services.outreach import OutreachService
from app.services.profile import ProfileReader
from app.workflow.graph import build_placement_graph
from app.workflow.state import PlacementWorkflowState

router = APIRouter(prefix="/workflow", tags=["workflow"])


class WorkflowStartRequest(ApiModel):
    query: DiscoveryText
    paper_limit: int = 20
    candidate_limit: int = 12
    generation_preference: str = "auto"


class WorkflowResumeRequest(ApiModel):
    selected_mentor_id: UUID
    selected_paper_ids: list[UUID]


def get_workflow_graph(request: Request) -> CompiledStateGraph:  # type: ignore[type-arg]
    """Build and compile the workflow graph with the persistent checkpointer."""
    checkpointer = request.app.state.workflow_checkpointer
    if checkpointer is None:
        checkpointer = MemorySaver()
    graph = build_placement_graph()
    return graph.compile(checkpointer=checkpointer)


@router.post("/start", summary="Start a new placement workflow")
async def start_workflow(
    request: WorkflowStartRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    graph: Annotated[CompiledStateGraph, Depends(get_workflow_graph)],  # type: ignore[type-arg]
) -> dict[str, str]:
    """Initialize a workflow run and return the thread ID."""
    thread_id = str(uuid4())
    config = cast(RunnableConfig, {"configurable": {"thread_id": thread_id}})

    state: PlacementWorkflowState = {
        "query": request.query,
        "owner_id": str(principal.owner_id),
        "paper_limit": request.paper_limit,
        "candidate_limit": request.candidate_limit,
        "generation_preference": request.generation_preference,
    }

    await graph.aupdate_state(config, state)
    return {"thread_id": thread_id}


@router.post("/{thread_id}/resume", summary="Provide human input to resume drafting")
async def resume_workflow(
    thread_id: str,
    request: WorkflowResumeRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    graph: Annotated[CompiledStateGraph, Depends(get_workflow_graph)],  # type: ignore[type-arg]
) -> dict[str, str]:
    """Update workflow state with mentor selection, readying it for the next run."""
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
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    graph: Annotated[CompiledStateGraph, Depends(get_workflow_graph)],  # type: ignore[type-arg]
    papers: Annotated[PaperDiscoveryReader, Depends(get_paper_discovery_service)],
    profiles: Annotated[ProfileReader, Depends(get_profile_service)],
    outreach_service: Annotated[OutreachService, Depends(get_outreach_service)],
) -> StreamingResponse:
    """Execute the workflow and stream events via Server-Sent Events."""

    settings: Settings = request.app.state.settings
    mentor_service = MentorDiscoveryService(
        papers=papers,
        profiles=profiles,
        weights=RelevanceWeights(
            query_evidence=settings.mentor_query_evidence_weight,
            profile_alignment=settings.mentor_profile_alignment_weight,
            supporting_depth=settings.mentor_supporting_depth_weight,
            recent_activity=settings.mentor_recent_activity_weight,
            evidence_completeness=settings.mentor_evidence_completeness_weight,
        ),
        evaluation_year=datetime.now(UTC).year,
    )

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
        except Exception as e:
            error_data = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
