"""Planner agent node — formulates multi-angle academic research vectors."""
from __future__ import annotations
import json
import structlog
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from src.agents.state import AgentState
from src.agents.llm_factory import create_llm

try:
    from langchain_groq import ChatGroq
except ImportError:
    ChatGroq = None

logger = structlog.get_logger()

PLANNER_SYSTEM = """You are an elite Academic Research Director and Methodologist.
Your mission is to decompose the user's research topic into rigorous, orthogonal scientific research vectors.

Guidelines for Academic Investigation:
1. Formulate specific, query-ready research vectors (not vague topics).
2. For each vector, specify:
   - title: concise title of the vector
   - search_query: precise academic search query optimized for scientific engines
   - target_engine: one of ["crossref", "arxiv", "pubmed", "web"] based on the subject:
     * "pubmed" for medical, health, biological, clinical, or pharmacological topics.
     * "arxiv" for computer science, artificial intelligence, physics, mathematics.
     * "crossref" for general science, engineering, economics, humanities, peer-reviewed journals.
     * "web" for recent developments, institutional datasets, or industry reports.
   - rationale: why this specific angle is critical for an authoritative, comprehensive paper.
3. Align depth:
   - "quick": exactly 3 vectors
   - "standard": exactly 5 vectors
   - "deep": exactly 7-8 vectors
4. Always prioritize empirical evidence, experimental data, and counter-perspectives to avoid bias."""


async def planner_node(state: AgentState) -> dict:
    """Break the research query into actionable, multi-source scientific search tasks."""
    depth = state.get("depth", "standard")
    target_count = 3 if depth == "quick" else (8 if depth == "deep" else 5)
    
    llm = create_llm(
        provider=state.get("provider"),
        model=state.get("model"),
        api_key=state.get("api_key"),
        auth_type=state.get("auth_type", "api_key"),
        base_url=state.get("base_url"),
        temperature=0.1,
    )

    from datetime import date
    as_of_date = date.today().isoformat()

    prompt = f"""Research Query: "{state['query']}"
Current Date (as_of): {as_of_date}
Depth Level: {depth.upper()} (Target: {target_count} vectors across functional lanes)
Domain Focus: {state.get('domain_focus', 'general')}
Output Language: {state.get('language', 'en')}

You must formulate:
1. A Bounded Research Contract:
   - as_of: "{as_of_date}"
   - decision_context: Clear operational or intellectual context
   - scope: Specific scope boundary (what is analyzed vs what is excluded)
   - must_resolve: 2-3 specific empirical sub-questions that must be proved
   - stop_when: "Evidence ledger contains sufficient primary/independent support or remaining gaps are explicit"
2. Lane-based Search Vectors:
   - LANE A (Primary Evidence): First-party docs, foundational papers, direct author formulations.
   - LANE B (Independent Validation): Independent peer evaluations, benchmark replications, empirical trials.
   - LANE C (Counter-Evidence & Limitations): Counterexamples, failure modes, trade-offs, and recent freshness checks.

Return ONLY valid JSON matching this schema:
{{
  "contract": {{
    "question": "{state['query']}",
    "as_of": "{as_of_date}",
    "decision_context": "Explanation of what this research informs",
    "scope": "Clear boundary of analysis",
    "must_resolve": ["Subquestion 1", "Subquestion 2"],
    "stop_when": "The comparison is supported or remaining gaps/unknowns are explicit"
  }},
  "vectors": [
    {{
      "lane": "primary | independent | counter",
      "title": "Concise vector title",
      "search_query": "specific search terms optimized for academic engines",
      "target_engine": "crossref | arxiv | pubmed | web",
      "rationale": "what this specific lane proves or tests"
    }}
  ]
}}"""

    messages = [
        SystemMessage(content=PLANNER_SYSTEM),
        HumanMessage(content=prompt),
    ]

    tasks = []
    contract = {
        "question": state["query"],
        "as_of": as_of_date,
        "decision_context": f"Authoritative academic analysis on {state['query']}",
        "scope": f"Scientific and empirical literature regarding {state['query']}",
        "must_resolve": [f"Theoretical foundation of {state['query']}", f"Empirical benchmark evidence for {state['query']}"],
        "stop_when": "The comparison is supported or remaining gaps/unknowns are explicit",
    }

    try:
        response = await llm.ainvoke(messages)
        content = response.content
        if isinstance(content, list):
            content = " ".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content])
        
        # Extract JSON from markdown blocks if present
        json_str = content
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        
        parsed = json.loads(json_str)
        tasks = parsed.get("vectors", [])
        if "contract" in parsed and isinstance(parsed["contract"], dict):
            contract = parsed["contract"]
    except Exception as e:
        logger.error("planner_structured_output_failed", error_type=type(e).__name__)
        # Fallback vectors organized by functional lanes
        domain = state.get("domain_focus", "general")
        primary_engine = "pubmed" if domain == "biomedical" else ("arxiv" if domain == "cs_ai" else "crossref")
        tasks = [
            {
                "lane": "primary",
                "title": "Theoretical Foundations & Primary Literature",
                "search_query": f"{state['query']} foundations literature review",
                "target_engine": primary_engine,
                "rationale": "Establish primary foundational definitions and baseline equations",
            },
            {
                "lane": "independent",
                "title": "Independent Empirical Benchmarks & Evaluations",
                "search_query": f"{state['query']} empirical evaluation benchmark results",
                "target_engine": "crossref",
                "rationale": "Gather independent replication and comparative test metrics",
            },
            {
                "lane": "counter",
                "title": "Limitations, Counter-Evidence & Freshness",
                "search_query": f"{state['query']} limitations challenges recent advances",
                "target_engine": "web",
                "rationale": "Discover caveats, edge cases, conflicting findings, and recent updates",
            },
        ]
        if target_count >= 5:
            tasks.extend([
                {
                    "lane": "independent",
                    "title": "Comparative Methodology & Architectures",
                    "search_query": f"{state['query']} comparative analysis approaches",
                    "target_engine": primary_engine,
                    "rationale": "Contrast competing methodological paradigms",
                },
                {
                    "lane": "primary",
                    "title": "Real-World Deployment & Case Studies",
                    "search_query": f"{state['query']} real world implementation case studies",
                    "target_engine": "web",
                    "rationale": "Verify practical performance claims in production",
                },
            ])

    step_log = {
        "node": "planner",
        "title": "Research Contract & Functional Lanes Formulated",
        "detail": f"Formulated bounded research contract and {len(tasks)} search lanes (Primary, Independent, Counter-evidence).",
        "contract": contract,
        "vectors": tasks,
    }

    logger.info("planner_done", job_id=state.get("job_id"), tasks_count=len(tasks))
    return {
        "contract": contract,
        "plan": tasks,
        "status": "researching",
        "step_logs": state.get("step_logs", []) + [step_log],
    }
