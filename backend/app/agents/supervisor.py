"""
Supervisor node.

Per the TDD, the Supervisor is orchestration-only: it understands the
request, builds an execution plan, decides which agents run, routes
the workflow, coordinates execution, and handles failures. It never
calls tools (no Tavily, no Gmail, no RAG) itself.

Module 5 has no Research/Knowledge/Personalization/Approval/Email
nodes yet — routing to any of them would be fake behavior wired to
nodes that don't exist. So this Supervisor is intentionally a real,
minimal pass-through: it receives a validated BusinessState, logs that
the workflow was received (genuine observability value, not a stub),
and returns state unchanged. Once Modules 6-10 add real nodes, this
function is where their conditional routing logic will actually live.
"""

import logging

from app.schemas.business_state import BusinessState

logger = logging.getLogger(__name__)


def supervisor_node(state: BusinessState) -> BusinessState:
    """
    Entry point for every workflow run.

    Contract every future node in this graph must follow: accept a
    BusinessState, return a BusinessState (LangGraph merges it back
    into the graph's state). This implementation deliberately does not
    mutate `state.status` — advancing it to a stage like RESEARCHING
    would imply a routing decision to a node that doesn't exist yet,
    which is exactly the fake behavior Module 5 is scoped to avoid.
    """
    logger.info(
        "Supervisor received workflow_id=%s for company=%s",
        state.session.workflow_id,
        state.input.company_name,
    )
    return state