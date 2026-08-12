"""
Research Agent node.

Owns everything research-related, per the approved Module 6 contract:
calling Tavily (primary, retried once), falling back to DDGS when
Tavily is unconfigured or exhausted, normalizing provider results into
ResearchData, and handling total failure.

Provider calls are isolated in _search_tavily/_search_ddgs so tests can
monkeypatch them directly. Tests must never call either provider live.

Module 6 does not use an LLM. Therefore:
    industry -> None
    products -> []

Those fields will be populated by a later module if reliable
structured extraction becomes available.
"""

import logging

from app.config.settings import get_settings
from app.models.workflow import WorkflowStatus
from app.schemas.business_state import BusinessState

logger = logging.getLogger(__name__)

# One initial attempt + one retry.
_MAX_TAVILY_ATTEMPTS = 2

# Limit the amount of provider content stored in business_summary.
_SUMMARY_MAX_CHARS = 500

# Maximum number of search results consumed.
_MAX_RESULTS = 5


def _search_tavily(company_name: str, api_key: str) -> dict:
    """
    Execute one Tavily search.

    Provider exceptions intentionally propagate to research_node(),
    where retry/fallback behavior is handled.
    """
    from tavily import TavilyClient

    client = TavilyClient(api_key=api_key)

    return client.search(
        query=company_name,
        include_answer=True,
        max_results=_MAX_RESULTS,
    )


def _search_ddgs(company_name: str) -> list[dict]:
    """
    Execute one DDGS search.

    Provider exceptions intentionally propagate to research_node().
    """
    from ddgs import DDGS

    with DDGS() as ddgs:
        return list(
            ddgs.text(
                company_name,
                max_results=_MAX_RESULTS,
            )
        )


def _map_tavily_response(response: dict) -> dict | None:
    """
    Normalize a Tavily response.

    Returns None when the provider returned no usable results.
    """
    results = response.get("results") or []

    if not results:
        return None

    recent_news = [
        result["title"]
        for result in results
        if result.get("title")
    ]

    website = next(
        (
            str(result["url"])
            for result in results
            if result.get("url")
        ),
        None,
    )

    business_summary = response.get("answer")

    if business_summary:
        business_summary = str(business_summary)[:_SUMMARY_MAX_CHARS]

    if not business_summary:
        for result in results:
            content = result.get("content")

            if content:
                business_summary = str(content)[:_SUMMARY_MAX_CHARS]
                break

    # A result containing at least a title, URL, or content is usable.
    has_usable_data = bool(
        website
        or recent_news
        or business_summary
    )

    if not has_usable_data:
        return None

    return {
        "website": website,
        "recent_news": recent_news,
        "business_summary": business_summary,
    }


def _map_ddgs_response(results: list[dict]) -> dict | None:
    """
    Normalize DDGS results.

    Returns None when DDGS returned no usable results.
    """
    if not results:
        return None

    recent_news = [
        result["title"]
        for result in results
        if result.get("title")
    ]

    website = next(
        (
            str(result["href"])
            for result in results
            if result.get("href")
        ),
        None,
    )

    business_summary = None

    for result in results:
        body = result.get("body")

        if body:
            business_summary = str(body)[:_SUMMARY_MAX_CHARS]
            break

    has_usable_data = bool(
        website
        or recent_news
        or business_summary
    )

    if not has_usable_data:
        return None

    return {
        "website": website,
        "recent_news": recent_news,
        "business_summary": business_summary,
    }


def _mark_research_failed(
    state: BusinessState,
    company_name: str,
) -> BusinessState:
    """Mark the workflow as failed after all research providers fail."""
    state.research.research_completed = False
    state.error_message = (
        "Research failed: both Tavily and DDGS were unable "
        f"to return usable results for '{company_name}'."
    )
    state.status = WorkflowStatus.FAILED

    return state


def research_node(state: BusinessState) -> BusinessState:
    """
    Research the workflow's target company.

    Provider order:

    1. Tavily when TAVILY_API_KEY is configured.
    2. Retry Tavily once after failure or unusable results.
    3. DDGS fallback.
    4. FAILED when no provider returns usable results.

    Provider failures never escape this node.
    """
    company_name = state.input.company_name.strip()

    if not company_name:
        logger.warning(
            "Research skipped: empty company_name for workflow_id=%s",
            state.session.workflow_id,
        )

        state.research.research_completed = False
        state.error_message = (
            "Cannot research: company_name is empty."
        )
        state.status = WorkflowStatus.FAILED

        return state

    settings = get_settings()

    mapped: dict | None = None

    # ---------------------------------------------------------------
    # Tavily
    # ---------------------------------------------------------------

    if settings.TAVILY_API_KEY.strip():
        for attempt in range(1, _MAX_TAVILY_ATTEMPTS + 1):
            try:
                response = _search_tavily(
                    company_name,
                    settings.TAVILY_API_KEY,
                )

                mapped = _map_tavily_response(response)

                if mapped is not None:
                    logger.info(
                        "Tavily research succeeded for "
                        "workflow_id=%s on attempt %d/%d",
                        state.session.workflow_id,
                        attempt,
                        _MAX_TAVILY_ATTEMPTS,
                    )
                    break

                logger.warning(
                    "Tavily attempt %d/%d returned no usable "
                    "results for workflow_id=%s",
                    attempt,
                    _MAX_TAVILY_ATTEMPTS,
                    state.session.workflow_id,
                )

            except Exception as exc:
                logger.warning(
                    "Tavily search attempt %d/%d failed for "
                    "workflow_id=%s: %s",
                    attempt,
                    _MAX_TAVILY_ATTEMPTS,
                    state.session.workflow_id,
                    exc,
                )
    else:
        logger.info(
            "No TAVILY_API_KEY configured; skipping Tavily "
            "for workflow_id=%s",
            state.session.workflow_id,
        )

    # ---------------------------------------------------------------
    # DDGS fallback
    # ---------------------------------------------------------------

    if mapped is None:
        try:
            ddgs_results = _search_ddgs(company_name)
            mapped = _map_ddgs_response(ddgs_results)

            if mapped is not None:
                logger.info(
                    "DDGS fallback succeeded for workflow_id=%s",
                    state.session.workflow_id,
                )

        except Exception as exc:
            logger.error(
                "DDGS fallback failed for workflow_id=%s: %s",
                state.session.workflow_id,
                exc,
            )

    # ---------------------------------------------------------------
    # Complete failure
    # ---------------------------------------------------------------

    if mapped is None:
        return _mark_research_failed(
            state,
            company_name,
        )

    # ---------------------------------------------------------------
    # Successful research
    # ---------------------------------------------------------------

    state.research.website = mapped.get("website")
    state.research.recent_news = (
        mapped.get("recent_news") or []
    )
    state.research.business_summary = (
        mapped.get("business_summary")
    )

    # Deliberately not populated in Module 6.
    state.research.industry = None
    state.research.products = []

    state.research.research_completed = True

    # Clear any previous error from this workflow state.
    state.error_message = None

    # Remain at RESEARCHING.
    # Module 7 will own the transition to RETRIEVING_KNOWLEDGE.
    state.status = WorkflowStatus.RESEARCHING

    return state
