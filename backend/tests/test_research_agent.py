"""
Tests for app.agents.research — the Research Agent node.

Every test mocks _search_tavily and/or _search_ddgs directly via
monkeypatch; none of these tests call a real Tavily or DuckDuckGo API,
matching CI's actual capabilities (no external network route) and the
approved Module 6 contract's testing requirements.
"""

import uuid

import pytest

from app.models.workflow import WorkflowStatus
from app.schemas.business_state import BusinessState, SessionInfo, WorkflowInput

import app.agents.research as research_module
from app.agents.research import research_node


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


_TAVILY_SUCCESS_RESPONSE = {
    "answer": "Acme Corp is a leading widget manufacturer.",
    "results": [
        {
            "title": "Acme Corp raises Series B",
            "url": "https://acme.example.com",
            "content": "Acme Corp announced today...",
        },
        {
            "title": "Acme Corp launches new product line",
            "url": "https://news.example.com/acme",
            "content": "In other news...",
        },
    ],
}

_DDGS_SUCCESS_RESULTS = [
    {
        "title": "Acme Corp - Official Site",
        "href": "https://acme.example.com",
        "body": "Acme Corp builds widgets for the modern era.",
    },
]


@pytest.fixture(autouse=True)
def _tavily_key_configured(monkeypatch):
    """Most tests assume TAVILY_API_KEY is set; the no-key test
    overrides this explicitly."""
    settings = research_module.get_settings()
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "tvly-fake-key-for-tests")
    yield


# --- Tavily success (first attempt) -----------------------------------


def test_tavily_success_on_first_attempt(monkeypatch):
    calls = []

    def fake_search_tavily(company_name, api_key):
        calls.append(company_name)
        return _TAVILY_SUCCESS_RESPONSE

    def fake_search_ddgs(company_name):
        raise AssertionError("DDGS should not be called when Tavily succeeds")

    monkeypatch.setattr(research_module, "_search_tavily", fake_search_tavily)
    monkeypatch.setattr(research_module, "_search_ddgs", fake_search_ddgs)

    state = research_node(_minimal_state())

    assert len(calls) == 1
    assert state.research.research_completed is True
    assert state.research.website == "https://acme.example.com"
    assert state.research.business_summary == "Acme Corp is a leading widget manufacturer."
    assert state.research.recent_news == [
        "Acme Corp raises Series B",
        "Acme Corp launches new product line",
    ]
    assert state.error_message is None


# --- Tavily fails once, succeeds on retry -------------------------------


def test_tavily_fails_once_then_succeeds_on_retry(monkeypatch):
    call_count = {"n": 0}

    def fake_search_tavily(company_name, api_key):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise ConnectionError("simulated transient failure")
        return _TAVILY_SUCCESS_RESPONSE

    monkeypatch.setattr(research_module, "_search_tavily", fake_search_tavily)

    state = research_node(_minimal_state())

    assert call_count["n"] == 2
    assert state.research.research_completed is True
    assert state.research.website == "https://acme.example.com"


# --- Tavily fails twice -> DDGS fallback succeeds ------------------------


def test_tavily_fails_twice_then_ddgs_fallback_succeeds(monkeypatch):
    tavily_calls = {"n": 0}
    ddgs_calls = {"n": 0}

    def fake_search_tavily(company_name, api_key):
        tavily_calls["n"] += 1
        raise ConnectionError("simulated persistent failure")

    def fake_search_ddgs(company_name):
        ddgs_calls["n"] += 1
        return _DDGS_SUCCESS_RESULTS

    monkeypatch.setattr(research_module, "_search_tavily", fake_search_tavily)
    monkeypatch.setattr(research_module, "_search_ddgs", fake_search_ddgs)

    state = research_node(_minimal_state())

    assert tavily_calls["n"] == 2  # exactly 1 initial + 1 retry, per the contract
    assert ddgs_calls["n"] == 1
    assert state.research.research_completed is True
    assert state.research.website == "https://acme.example.com"
    assert state.research.business_summary == "Acme Corp builds widgets for the modern era."
    assert state.research.recent_news == ["Acme Corp - Official Site"]
    assert state.error_message is None


# --- Both providers fail --------------------------------------------------


def test_both_providers_fail(monkeypatch):
    def fake_search_tavily(company_name, api_key):
        raise ConnectionError("tavily down")

    def fake_search_ddgs(company_name):
        raise ConnectionError("ddgs down")

    monkeypatch.setattr(research_module, "_search_tavily", fake_search_tavily)
    monkeypatch.setattr(research_module, "_search_ddgs", fake_search_ddgs)

    state = research_node(_minimal_state())

    assert state.research.research_completed is False
    assert state.error_message is not None
    assert "Acme Corp" in state.error_message
    assert state.status == WorkflowStatus.FAILED
    # Schema defaults remain untouched on total failure.
    assert state.research.website is None
    assert state.research.recent_news == []
    assert state.research.business_summary is None


# --- Empty company name ----------------------------------------------------


def test_empty_company_name_skips_both_providers(monkeypatch):
    def fake_search_tavily(company_name, api_key):
        raise AssertionError("Tavily should not be called for an empty company name")

    def fake_search_ddgs(company_name):
        raise AssertionError("DDGS should not be called for an empty company name")

    monkeypatch.setattr(research_module, "_search_tavily", fake_search_tavily)
    monkeypatch.setattr(research_module, "_search_ddgs", fake_search_ddgs)

    state = _minimal_state(
        input=WorkflowInput(
            company_name="   ",  # whitespace-only
            recipient_email="contact@acme.com",
            purpose="Partnership outreach",
        )
    )

    result = research_node(state)

    assert result.research.research_completed is False
    assert result.error_message == "Cannot research: company_name is empty."
    assert result.status == WorkflowStatus.FAILED


# --- ResearchData mapping correctness --------------------------------------


def test_tavily_mapping_falls_back_to_content_when_no_answer(monkeypatch):
    response_without_answer = {
        "results": [
            {
                "title": "Acme news",
                "url": "https://acme.example.com",
                "content": "A" * 900,  # longer than the 500-char summary cap
            }
        ]
    }

    def fake_search_tavily(company_name, api_key):
        return response_without_answer

    monkeypatch.setattr(research_module, "_search_tavily", fake_search_tavily)

    state = research_node(_minimal_state())

    assert state.research.business_summary == "A" * 500  # truncated correctly
    assert state.research.industry is None  # never populated, per the contract
    assert state.research.products == []  # never populated, per the contract


# def test_tavily_mapping_handles_empty_results_list(monkeypatch):
#     def fake_search_tavily(company_name, api_key):
#         return {"results": [], "answer": None}

#     monkeypatch.setattr(research_module, "_search_tavily", fake_search_tavily)

#     state = research_node(_minimal_state())

#     assert state.research.research_completed is True  # call succeeded, just sparse
#     assert state.research.website is None
#     assert state.research.recent_news == []
#     assert state.research.business_summary is None


def test_tavily_empty_results_falls_back_to_ddgs(monkeypatch):
    tavily_calls = {"n": 0}
    ddgs_calls = {"n": 0}

    def fake_search_tavily(company_name, api_key):
        tavily_calls["n"] += 1
        return {"results": [], "answer": None}

    def fake_search_ddgs(company_name):
        ddgs_calls["n"] += 1
        return _DDGS_SUCCESS_RESULTS

    monkeypatch.setattr(
        research_module,
        "_search_tavily",
        fake_search_tavily,
    )
    monkeypatch.setattr(
        research_module,
        "_search_ddgs",
        fake_search_ddgs,
    )

    state = research_node(_minimal_state())

    # Empty Tavily results are not usable, so Tavily is retried once.
    assert tavily_calls["n"] == 2

    # After Tavily is exhausted, DDGS is used as the fallback.
    assert ddgs_calls["n"] == 1

    # DDGS produced usable research data.
    assert state.research.research_completed is True
    assert state.research.website == "https://acme.example.com"
    assert state.research.business_summary == (
        "Acme Corp builds widgets for the modern era."
    )
    assert state.research.recent_news == ["Acme Corp - Official Site"]

    # Research succeeded, so the workflow remains at the Research stage.
    assert state.status == WorkflowStatus.RESEARCHING
    assert state.error_message is None


# --- No API key behavior ---------------------------------------------------


def test_no_api_key_skips_tavily_and_uses_ddgs_directly(monkeypatch):
    settings = research_module.get_settings()
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "")

    tavily_calls = {"n": 0}

    def fake_search_tavily(company_name, api_key):
        tavily_calls["n"] += 1
        raise AssertionError("Tavily must not be called when no API key is configured")

    def fake_search_ddgs(company_name):
        return _DDGS_SUCCESS_RESULTS

    monkeypatch.setattr(research_module, "_search_tavily", fake_search_tavily)
    monkeypatch.setattr(research_module, "_search_ddgs", fake_search_ddgs)

    state = research_node(_minimal_state())

    assert tavily_calls["n"] == 0
    assert state.research.research_completed is True
    assert state.research.website == "https://acme.example.com"


# --- BusinessState preservation --------------------------------------------


def test_research_preserves_unrelated_state_fields(monkeypatch):
    def fake_search_tavily(company_name, api_key):
        return _TAVILY_SUCCESS_RESPONSE

    monkeypatch.setattr(research_module, "_search_tavily", fake_search_tavily)

    workflow_id = uuid.uuid4()
    state = _minimal_state(
        session=SessionInfo(
            workflow_id=workflow_id, organization_id=uuid.uuid4(), user_id=uuid.uuid4()
        )
    )

    result = research_node(state)

    assert result.session.workflow_id == workflow_id
    assert result.input.company_name == "Acme Corp"
    assert result.knowledge.retrieved_chunks == []  # untouched, Module 7's concern
    assert result.approval.approval_status.value == "pending"  # untouched
