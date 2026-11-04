"""Malformed model output must never become a passing scientific verdict."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage

from src.agents.evidence import validate_claim
from src.agents.planner import planner_node
from src.agents.reviewer import reviewer_node
from src.agents.state import default_state
from src.agents.verifier import verifier_node
from src.agents.writer import writer_node


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"overall_score": 9},
        {"verdict": "ACCEPTED"},
        {"overall_score": 11, "verdict": "ACCEPTED"},
        {"overall_score": float("nan"), "verdict": "ACCEPTED"},
        {"overall_score": 9, "verdict": "unknown"},
    ],
)
async def test_missing_or_invalid_review_cannot_pass(payload):
    state = default_state("A question", "test")
    state["draft"] = "Research and uncertainty. " * 100
    model = AsyncMock()
    model.ainvoke.return_value = AIMessage(content=json.dumps(payload))
    with patch("src.agents.reviewer.create_llm", return_value=model):
        result = await reviewer_node(state)
    assert result["review_score"] == 0
    assert result["review_critique"]["verdict"] == "UNAVAILABLE"


@pytest.mark.asyncio
async def test_final_revision_still_reviews_its_new_draft():
    state = default_state("A question", "test", max_iterations=3)
    state.update(draft="New evidence and limitations. " * 100, revision_count=2, review_score=2)
    model = AsyncMock()
    model.ainvoke.return_value = AIMessage(content='{"overall_score":8.2,"verdict":"ACCEPTED"}')
    with patch("src.agents.reviewer.create_llm", return_value=model):
        result = await reviewer_node(state)
    model.ainvoke.assert_awaited_once()
    assert result["review_score"] == 8.2
    assert result["status"] == "done"


@pytest.mark.asyncio
async def test_empty_plan_uses_bounded_search_vectors():
    state = default_state("A question", "test")
    model = AsyncMock()
    model.ainvoke.return_value = AIMessage(content='{"vectors":[]}')
    with patch("src.agents.planner.create_llm", return_value=model):
        result = await planner_node(state)
    assert 3 <= len(result["plan"]) <= 8
    assert {vector["lane"] for vector in result["plan"]} >= {"primary", "independent", "counter"}


@pytest.mark.asyncio
async def test_empty_verifier_response_is_explicitly_unverified():
    state = default_state("A question", "test")
    state["sources"] = [{"source_id": "S-01", "title": "A paper", "snippet": "An abstract."}]
    model = AsyncMock()
    model.ainvoke.return_value = AIMessage(content="{}")
    with patch("src.agents.verifier.create_llm", return_value=model):
        result = await verifier_node(state)
    assert result["verification_report"]["supported_count"] == 0
    assert result["evidence_matrix"][0]["status"] == "unverified"


def test_source_numbers_come_from_corpus_instead_of_model_guess():
    sources = [
        {"source_id": "S-01", "snippet": "First"},
        {"source_id": "S-02", "snippet": "Second", "source_type": "arxiv"},
    ]
    claim = validate_claim(
        {
            "status": "supported",
            "supporting_source_indices": [999],
            "evidence": [
                {
                    "source_id": "S-02",
                    "passage": "Second",
                    "stance": "supports",
                    "source_type": "journal",
                }
            ],
        },
        sources,
        0,
        "2026-11-04",
    )
    assert claim["supporting_source_indices"] == [2]
    assert claim["evidence"][0]["source_type"] == "arxiv"


def test_contested_requires_distinct_support_and_counter_sources():
    sources = [{"source_id": "S-01", "snippet": "A result."}]
    claim = validate_claim(
        {
            "status": "contested",
            "evidence": [{"source_id": "S-01", "passage": "A result.", "stance": "supports"}],
        },
        sources,
        0,
        "2026-11-04",
    )
    assert claim["status"] == "unverified"


@pytest.mark.asyncio
async def test_writer_includes_source_records_beyond_thirty():
    state = default_state("A question", "test")
    state["sources"] = [
        {"source_id": f"S-{i:02d}", "title": f"Source {i}", "url": f"https://example.org/{i}"}
        for i in range(1, 36)
    ]
    model = AsyncMock()
    model.ainvoke.return_value = AIMessage(content="# Report\n\nUncertainty remains.")
    with patch("src.agents.writer.create_llm", return_value=model):
        await writer_node(state)
    prompt = model.ainvoke.await_args.args[0][1].content
    assert "[35]" in prompt and "Source 35" in prompt
    assert "retrieved source records" in prompt


@pytest.mark.asyncio
async def test_writer_rejects_truncated_output():
    state = default_state("A question", "test")
    model = AsyncMock()
    model.ainvoke.return_value = AIMessage(
        content="Partial report", response_metadata={"finish_reason": "length"}
    )
    with patch("src.agents.writer.create_llm", return_value=model):
        with pytest.raises(RuntimeError):
            await writer_node(state)
