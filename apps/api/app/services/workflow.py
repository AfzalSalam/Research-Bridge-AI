"""Authorization for private checkpointed workflow state."""

from typing import cast
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from app.core.errors import AppError


async def require_workflow_owner(
    graph: CompiledStateGraph,  # type: ignore[type-arg]
    thread_id: str,
    owner_id: UUID,
) -> None:
    """Hide missing and foreign workflows behind the same safe response."""

    config = cast(RunnableConfig, {"configurable": {"thread_id": thread_id}})
    snapshot = await graph.aget_state(config)
    if snapshot.values.get("owner_id") != str(owner_id):
        raise AppError(
            code="workflow_not_found",
            message="This workflow is unavailable in your workspace.",
            status_code=404,
        )
