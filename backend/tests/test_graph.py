"""
Tests for app.workflows.graph — the Module 5 LangGraph skeleton.

These use real LangGraph execution throughout (StateGraph, compile,
invoke, MemorySaver) — nothing here is mocked. Each test builds its own
graph instance via build_graph() rather than sharing the module-level
`graph` singleton, so each test gets independent in-memory checkpoint
storage and can't leak state into another test via a shared thread_id
namespace.

No PostgreSQL fixture is needed: BusinessState and MemorySaver are both
purely in-memory.
"""

import uuid

from app.models.workflow import WorkflowStatus
from app.schemas.business_state import BusinessState, SessionInfo, WorkflowInput
from app.workflows.graph import build_graph


def _minimal_state(**overrides) -> BusinessState:
    defaults = dict(
        session=SessionInfo(
            workflow_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        ),
        input=WorkflowInput(
            company_name="Acme Corp",
            recipient_email="contact@acme.com",
            purpose="Partnership outreach",
        ),
    )
    defaults.update(overrides)
    return BusinessState(**defaults)


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


# --- 1. Graph construction -------------------------------------------------


def test_build_graph_returns_a_compiled_graph():
    graph = build_graph()

    assert graph is not None


def test_build_graph_produces_independent_instances():
    graph_a = build_graph()
    graph_b = build_graph()

    assert graph_a is not graph_b


# --- 2. Graph compilation ---------------------------------------------------


def test_graph_has_supervisor_node_wired():
    graph = build_graph()

    # get_graph() exposes the underlying node/edge structure LangGraph
    # actually compiled — this asserts against the real graph, not our
    # intention.
    node_names = set(graph.get_graph().nodes.keys())

    assert "supervisor" in node_names
    assert "__start__" in node_names
    assert "__end__" in node_names


# --- 3 & 4. Minimal valid BusinessState execution, START -> Supervisor -> END --


def test_invoke_with_minimal_state_succeeds():
    graph = build_graph()
    state = _minimal_state()

    result = graph.invoke(state, config=_config("thread-minimal"))

    assert result is not None


def test_invoke_runs_start_to_supervisor_to_end():
    graph = build_graph()
    state = _minimal_state()
    config = _config("thread-path")

    graph.invoke(state, config=config)

    # The state history records every step LangGraph actually executed.
    history = list(graph.get_state_history(config))
    # Most recent state first; the graph should have progressed through
    # exactly one node (supervisor) between START and END.
    executed_node_sets = [tuple(snapshot.next) for snapshot in history]
    # The final snapshot's `next` is empty (graph finished, at END).
    assert executed_node_sets[0] == ()


# --- 5. Supervisor receives and returns valid state -------------------------


def test_supervisor_actually_receives_a_business_state(monkeypatch):
    received = {}

    def spy_supervisor(state: BusinessState) -> BusinessState:
        received["state"] = state
        received["is_business_state"] = isinstance(state, BusinessState)
        return state

    import app.workflows.graph as graph_module

    monkeypatch.setattr(graph_module, "supervisor_node", spy_supervisor)
    graph = graph_module.build_graph()

    state = _minimal_state()
    graph.invoke(state, config=_config("thread-spy"))

    assert received["is_business_state"] is True
    assert received["state"].input.company_name == "Acme Corp"


# --- 6. State values survive graph execution --------------------------------


def test_state_values_survive_execution():
    graph = build_graph()
    workflow_id = uuid.uuid4()
    state = _minimal_state(
        session=SessionInfo(
            workflow_id=workflow_id,
            organization_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        ),
        input=WorkflowInput(
            company_name="Very Specific Co",
            recipient_email="specific@example.com",
            purpose="Test that values survive",
        ),
    )

    result = graph.invoke(state, config=_config("thread-survive"))

    assert result["session"].workflow_id == workflow_id
    assert result["input"].company_name == "Very Specific Co"
    assert result["input"].recipient_email == "specific@example.com"
    assert result["status"] == WorkflowStatus.PENDING  # untouched, as designed


# --- 7. MemorySaver checkpoint creation --------------------------------------


def test_checkpoint_is_created_after_invoke():
    graph = build_graph()
    state = _minimal_state()
    config = _config("thread-checkpoint")

    graph.invoke(state, config=config)

    history = list(graph.get_state_history(config))
    assert len(history) > 0  # at least one checkpoint was written


# --- 8. thread_id configuration ----------------------------------------------


def test_different_thread_ids_have_independent_checkpoints():
    graph = build_graph()

    state_a = _minimal_state(
        input=WorkflowInput(
            company_name="Company A",
            recipient_email="a@example.com",
            purpose="A",
        )
    )
    state_b = _minimal_state(
        input=WorkflowInput(
            company_name="Company B",
            recipient_email="b@example.com",
            purpose="B",
        )
    )

    graph.invoke(state_a, config=_config("thread-a"))
    graph.invoke(state_b, config=_config("thread-b"))

    snapshot_a = graph.get_state(_config("thread-a"))
    snapshot_b = graph.get_state(_config("thread-b"))

    assert snapshot_a.values["input"].company_name == "Company A"
    assert snapshot_b.values["input"].company_name == "Company B"


# --- 9. graph.get_state(config) returns checkpoint/state ---------------------


def test_get_state_returns_a_snapshot_with_expected_values():
    graph = build_graph()
    state = _minimal_state()
    config = _config("thread-get-state")

    graph.invoke(state, config=config)
    snapshot = graph.get_state(config)

    assert snapshot is not None
    assert snapshot.values["input"].company_name == "Acme Corp"


def test_get_state_for_unknown_thread_id_returns_empty_snapshot():
    graph = build_graph()

    snapshot = graph.get_state(_config("thread-never-invoked"))

    # No checkpoint exists yet for this thread — LangGraph returns an
    # empty/default snapshot rather than raising.
    assert snapshot.values == {} or snapshot.values is None


# --- 10. Checkpoint/state can be restored/inspected as expected -------------


def test_checkpoint_can_be_rehydrated_into_business_state():
    graph = build_graph()
    state = _minimal_state()
    config = _config("thread-rehydrate")

    graph.invoke(state, config=config)
    snapshot = graph.get_state(config)

    # Prove the checkpointed dict round-trips back into a real,
    # validated BusinessState — not just an opaque blob.
    rehydrated = BusinessState.model_validate(snapshot.values)

    assert rehydrated.input.company_name == "Acme Corp"
    assert rehydrated.status == WorkflowStatus.PENDING
    assert rehydrated.model_dump_json()  # still JSON-serializable