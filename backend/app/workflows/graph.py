"""
LangGraph StateGraph skeleton.

Builds the graph every future agent (Modules 7-10) will be added to as
a node. As of Module 6: START -> Supervisor -> Research -> END. The
pipeline is deliberately linear here, matching the TDD's own linear
workflow diagram (Supervisor -> Research -> Knowledge -> ... ->
Completed) — conditional edges aren't needed until Module 9 introduces
an approve/reject branch. Retry/fallback within the Research stage
(Tavily -> retry -> DDGS) is the Research Agent's own internal logic,
not a graph-level concern.

Verified directly (not assumed) against langgraph==1.2.10 /
langchain-core==1.5.3 before this file was first written (Module 5):
  - StateGraph(BusinessState) — a Pydantic BaseModel — constructs correctly
  - a node function typed (state: BusinessState) -> BusinessState works
  - graph.compile()/.invoke() succeed
  - MemorySaver checkpoints the state and graph.get_state(config) retrieves it
  - the state remains JSON-serializable via BusinessState.model_dump_json()
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.research import research_node
from app.agents.supervisor import supervisor_node
from app.models.workflow import WorkflowStatus
from app.schemas.business_state import (
    ApprovalData,
    ApprovalStatus,
    BusinessState,
    EmailData,
    KnowledgeData,
    PersonalizationData,
    ResearchData,
    SessionInfo,
    WorkflowInput,
)

# Every custom (non-builtin) type nested inside BusinessState must be
# explicitly allow-listed for the checkpointer's msgpack serializer.
# Without this, checkpointing still works today but logs a warning that
# a future LangGraph version will refuse to deserialize checkpoints
# containing unregistered types — discovered during Module 5's
# pre-implementation verification, fixed here rather than ignored.
_ALLOWED_MSGPACK_MODULES: list[tuple[str, str]] = [
    ("app.schemas.business_state", cls.__name__)
    for cls in (
        SessionInfo,
        WorkflowInput,
        ResearchData,
        KnowledgeData,
        PersonalizationData,
        ApprovalStatus,
        ApprovalData,
        EmailData,
    )
] + [("app.models.workflow", WorkflowStatus.__name__)]


def build_graph() -> CompiledStateGraph:
    """
    Construct and compile the workflow graph.

    Exposed as a function — not just the module-level `graph` singleton
    below — so tests can build independent graph instances with their
    own isolated in-memory checkpoint storage, instead of sharing
    checkpoint state across test cases via a single shared graph.
    """
    builder = StateGraph(BusinessState)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("research", research_node)
    builder.add_edge(START, "supervisor")
    builder.add_edge("supervisor", "research")
    builder.add_edge("research", END)

    checkpointer = MemorySaver(
        serde=JsonPlusSerializer(allowed_msgpack_modules=_ALLOWED_MSGPACK_MODULES)
    )
    return builder.compile(checkpointer=checkpointer)


# A single compiled graph instance, reused across the process — mirrors
# app.database.session.engine being created once rather than per call.
# Module 11 (workflow orchestration API) will be the first real caller
# of this outside of tests.
#
# Named `compiled_graph`, NOT `graph` — this module is itself named
# graph.py, and app/workflows/__init__.py re-exports this singleton.
# `from app.workflows.graph import graph` would silently overwrite the
# `app.workflows.graph` submodule *attribute* on the package with this
# object (since the imported name and the submodule name would be
# identical), breaking any later `import app.workflows.graph` elsewhere
# in the codebase. Discovered via a real test failure, not theoretical.
compiled_graph = build_graph()
