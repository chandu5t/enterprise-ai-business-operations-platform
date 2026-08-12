"""
Supervisor node.

Per the TDD, the Supervisor is orchestration-only: it understands the
request, builds an execution plan, decides which agents run, routes the
workflow, coordinates execution, and handles failures. It never
calls tools (no Tavily, no Gmail, no RAG) itself.

Module 6 adds the first real downstream node (Research), so the
Supervisor advancing state.status to RESEARCHING is now an honest
routing signal rather than the fake progression Module 5 deliberately
avoided (there was nothing real to route to yet). This function is
where each future agent's conditional routing logic will continue
to be added as Modules 7-10 introduce their own nodes.
"""

import logging

from app.models.workflow import WorkflowStatus
from app.schemas.business_state import BusinessState

logger = logging.getLogger(__name__)


def supervisor_node(state: BusinessState) -> BusinessState:
    """
    Entry point for every workflow run.

    Contract every node in this graph follows: accept a BusinessState,
    return a BusinessState (LangGraph merges it back into the graph's
    state). Sets status to RESEARCHING — the only stage that currently
    has a real node (Research, Module 6) to receive it. Does not call
    Tavily, DDGS, or any other tool itself; that logic belongs entirely
    to research_node.
    """
    logger.info(
        "Supervisor received workflow_id=%s for company=%s — routing to research",
        state.session.workflow_id,
        state.input.company_name,
    )

    state.status = WorkflowStatus.RESEARCHING

    return state
