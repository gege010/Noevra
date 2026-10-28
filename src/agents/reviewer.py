"""Peer Reviewer agent node — acts as an exacting scientific referee evaluating paper rigor."""
from __future__ import annotations
import json
import structlog
from langchain_core.messages import SystemMessage, HumanMessage
from src.agents.state import AgentState
from src.agents.llm_factory import create_llm

logger = structlog.get_logger()

REVIEWER_SYSTEM = """You are an Academic Journal Referee and Editorial Board Member.
Your mandate is to critically evaluate submitted research papers using the Research Machine Engineering Rubric:

Evaluation Dimensions:
1. **Support (Weight: 25%):**
   - Do inline citations `[N]` directly support the claims they follow?
   - Are there unsupported generalizations or unanchored assertions?
2. **Coverage (Weight: 20%):**
   - Did the paper address the Research Contract's must-resolve subquestions and decision context?
3. **Freshness & Temporal Anchor (Weight: 15%):**
   - Are time-sensitive claims, latest models, and recent developments anchored to the stated date?
4. **Contradiction Surfacing (Weight: 15%):**
   - Did the system identify and analyze divergences between studies rather than averaging them away?
5. **Calibration & Unknowns (Weight: 15%):**
   - Did the paper explicitly label what the evidence DOES NOT settle instead of guessing?
6. **Scholarly Rigor & Tone (Weight: 10%):**
   - Objective, conservative, didactic tone without sensationalist buzzwords.

Decision Rules:
- Score >= 7.5: Pass (Accept with minor or no revisions)
- Score < 7.5: Request Targeted Revision (Specify exactly which claims remain unverified or contested)"""


async def reviewer_node(state: AgentState) -> dict:
    """Evaluate draft quality and determine whether revision or finalization is required."""
    draft = state.get("draft", "")
    contract = state.get("contract", {})
    evidence_matrix = state.get("evidence_matrix", [])
    revision_count = state.get("revision_count", 0)
    max_revisions = min(2, max(0, state.get("max_iterations", 3) - 1))

    # If draft is empty or too short
    if not draft or len(draft.split()) < 200:
        return {
            "review_score": 3.0,
            "review_critique": {"verdict": "REJECT", "feedback": "Draft too brief or missing substantive content."},
            "status": "done" if revision_count >= max_revisions else "researching",
            "gap_analysis": "Draft lacked sufficient length and substance. Expand search on core methodology.",
            "revision_count": revision_count + 1,
        }

    # If max revisions reached, approve with editorial notice
    if revision_count >= max_revisions:
        logger.info("reviewer_max_revisions_reached", job_id=state.get("job_id"))
        step_log = {
            "node": "reviewer",
            "title": "Research budget exhausted",
            "detail": f"Stopped after {revision_count} revision cycles; human review required.",
            "score": state.get("review_score", 0),
            "verdict": "BUDGET_EXHAUSTED",
        }
        return {
            "status": "done",
            "step_logs": state.get("step_logs", []) + [step_log],
        }

    llm = create_llm(
        provider=state.get("provider"),
        model=state.get("model"),
        api_key=state.get("api_key"),
        auth_type=state.get("auth_type", "api_key"),
        base_url=state.get("base_url"),
        temperature=0.1,
    )

    prompt = f"""Review the following draft paper against its Research Contract and Evidence Ledger:

--- RESEARCH CONTRACT ---
{json.dumps(contract, indent=2)}

--- EVIDENCE LEDGER SUMMARY ({len(evidence_matrix)} items) ---
{json.dumps([{"claim_id": e.get("claim_id"), "claim": e.get("claim"), "status": e.get("status")} for e in evidence_matrix[:15]], indent=2)}

--- DRAFT PAPER ---
{draft[:12000]}
--- END OF PAPER ---

Return ONLY valid JSON matching this schema:
{{
  "overall_score": 8.5,
  "verdict": "ACCEPTED | REVISE",
  "dimensions": {{
    "support_score": 8.5,
    "coverage_score": 8.0,
    "freshness_score": 9.0,
    "contradictions_score": 8.5,
    "calibration_score": 8.0,
    "rigor_score": 9.0
  }},
  "strengths": ["Key strength 1", "Key strength 2"],
  "weaknesses": ["Key weakness 1"],
  "actionable_gaps": "Specific prompt instruction for targeted researcher pass if REVISE, or empty string if ACCEPTED",
  "unverified_claims": ["Specific claims that still lack direct evidence"],
  "contested_claims": ["Specific conflicts that need deeper comparative analysis"]
}}"""

    messages = [
        SystemMessage(content=REVIEWER_SYSTEM),
        HumanMessage(content=prompt),
    ]

    score = 8.5
    verdict = "ACCEPTED"
    critique = {}
    gap_analysis = None
    targeted_unverified = []
    targeted_contested = []

    try:
        response = await llm.ainvoke(messages)
        content = response.content
        if isinstance(content, list):
            content = " ".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content])
        
        json_str = content
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()

        parsed = json.loads(json_str)
        score = float(parsed.get("overall_score", 8.0))
        verdict = parsed.get("verdict", "ACCEPTED")
        critique = parsed
        gap_analysis = parsed.get("actionable_gaps") if verdict == "REVISE" else None
        targeted_unverified = parsed.get("unverified_claims", [])
        targeted_contested = parsed.get("contested_claims", [])
    except Exception as e:
        logger.error("reviewer_evaluation_failed", error_type=type(e).__name__)
        score = 0.0
        verdict = "UNAVAILABLE"
        critique = {
            "overall_score": None,
            "verdict": "UNAVAILABLE",
            "strengths": [],
            "weaknesses": ["Automated review failed; human review is required."],
        }


    passed = (score >= 7.5 and verdict == "ACCEPTED")
    budget_exhausted = len(state.get("sources", [])) >= state.get("sources_limit", 20) or state.get("current_iteration", 0) >= state.get("max_iterations", 10)
    stop = passed or verdict == "UNAVAILABLE" or revision_count >= max_revisions or budget_exhausted

    step_log = {
        "node": "reviewer",
        "title": "Peer Review Complete",
        "detail": f"Automated review: {verdict}; score {score}/10." + (" Source or iteration budget reached; unresolved findings remain for human review." if budget_exhausted and not passed else ""),
        "score": score,
        "critique": critique,
    }

    logger.info("reviewer_decision", job_id=state.get("job_id"), score=score, passed=passed)

    if stop:
        return {
            "review_score": score,
            "review_critique": critique,
            "status": "done",
            "step_logs": state.get("step_logs", []) + [step_log],
        }
    else:
        return {
            "review_score": score,
            "review_critique": critique,
            "gap_analysis": gap_analysis or "Targeted investigation required for contested and unverified claims",
            "unverified_claims": targeted_unverified,
            "contested_claims": targeted_contested,
            "revision_count": revision_count + 1,
            "status": "researching",
            "step_logs": state.get("step_logs", []) + [step_log],
        }
