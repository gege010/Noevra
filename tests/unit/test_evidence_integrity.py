from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from src.agents.evidence import validate_claim
from src.agents.state import default_state
from src.agents.verifier import verifier_node
from src.agents.reviewer import reviewer_node
from src.schemas.requests import ResearchRequest


def test_fabricated_passage_and_url_cannot_pass():
    sources = [{"source_id": "S-01", "passage": "Observed in ten participants.", "url": "https://example.org/paper"}]
    claim = {"status": "supported", "evidence": [{"source_id": "S-01", "passage": "Proven universally.", "stance": "supports"}]}
    assert validate_claim(claim, sources, 0, "2026-10-28")["status"] == "unverified"
    claim["evidence"][0].update(passage="Observed in ten participants.", url="https://invented.invalid")
    result = validate_claim(claim, sources, 0, "2026-10-28")
    assert result["status"] == "supported"
    assert result["evidence"][0]["url"] == sources[0]["url"]


@pytest.mark.asyncio
async def test_verification_failure_never_confirms_metadata():
    state = default_state("test question", "test")
    state["sources"] = [{"title": "A paper", "snippet": "An abstract"}]
    llm = MagicMock(ainvoke=AsyncMock(side_effect=ValueError("invalid response")))
    with patch("src.agents.verifier.create_llm", return_value=llm):
        result = await verifier_node(state)
    assert result["verification_report"]["supported_count"] == 0
    assert result["unverified_claims"][0]["status"] == "unverified"


@pytest.mark.asyncio
async def test_review_failure_does_not_invent_passing_score():
    llm = MagicMock(ainvoke=AsyncMock(side_effect=ValueError("invalid response")))
    state = default_state("test question", "test")
    state["draft"] = "Evidence and limitations. " * 100
    with patch("src.agents.reviewer.create_llm", return_value=llm):
        result = await reviewer_node(state)
    assert result["review_critique"]["verdict"] == "UNAVAILABLE"
    assert result["review_score"] == 0


@pytest.mark.parametrize("values", [{"query": "   "}, {"query": "valid", "include_web": False, "include_academic": False}, {"query": "valid", "provider": "unknown"}])
def test_invalid_research_configuration(values):
    with pytest.raises(ValidationError):
        ResearchRequest(**values)
