"""Academic Writer agent node — synthesizes publication-grade research monographs."""
from __future__ import annotations
import json
import structlog
from langchain_core.messages import SystemMessage, HumanMessage
from src.agents.state import AgentState
from src.agents.llm_factory import create_llm

logger = structlog.get_logger()

WRITER_SYSTEM = """You are a Distinguished Academic Fellow and Senior Scientific Editor.
Your objective is to author an authoritative, publication-ready Academic Research Monograph based STRICTLY on verified empirical evidence and retrieved literature.

Academic Tone and Stylistic Guidelines:
1. **Conservative, Rigorous, and Educational:**
   - Avoid sensationalist buzzwords, hyperbole, and speculative puffery.
   - Employ measured, exact academic terminology (e.g., "empirical data suggests", "statistically significant correlation", "methodological constraints demonstrate").
   - Balance scholarly depth with didactic clarity so that a domain researcher or technical executive can digest complex nuances.
2. **Zero Hallucination & Dense Inline Citation:**
   - Anchor every scientific assertion, benchmark, or historical claim to specific sources using bracketed numeric markers `[1]`, `[2]` or author-year citations `(Vaswani et al., 2017)`.
   - Never invent paper titles, authors, or data points not present in the provided evidence.
3. **Structured Academic Architecture:**
   - **# Title** (Scholarly, precise, non-clickbait)
   - **## Abstract** (Structured: Background, Objectives, Corpus & Methodology, Key Empirical Findings, Epistemic Implications)
   - **## 1. Introduction & Contextual Background**
   - **## 2. Theoretical Framework & Methodological Taxonomy**
   - **## 3. Systematic Literature Review & Evidence Synthesis** (Deep narrative with dense inline citations)
   - **## 4. Quantitative Synthesis & Comparative Benchmark Table** (Must include at least one detailed Markdown table comparing methodologies, metrics, or performance)
   - **## 5. Critical Analysis, Contradictions, & Methodological Limitations**
   - **## 6. Strategic Implications & Future Research Horizons**
   - **## 7. References** (Comprehensive bibliography matching inline citations with Authors, Title, Journal/Preprint, Year, and DOI/URL links).
4. **Language:**
   - Write in the requested language (English or Bahasa Indonesia) maintaining uncompromising academic formality throughout."""


async def writer_node(state: AgentState) -> dict:
    """Synthesize verified sources and evidence matrix into an academic research paper."""
    query = state.get("query")
    depth = state.get("depth", "standard")
    language = state.get("language", "en")
    citation_style = state.get("citation_style", "ieee")
    sources = state.get("sources", [])
    evidence_matrix = state.get("evidence_matrix", [])
    verification_report = state.get("verification_report", {})

    # Build reference mapping
    ref_list = []
    for idx, s in enumerate(sources[:30]):
        authors = s.get("authors", [])
        author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
        if not author_str:
            author_str = "Anonymous / Institutional Author"
        year = s.get("published_date", "") or "n.d."
        doi = s.get("doi", "")
        url = s.get("url", "")
        journal = s.get("journal") or s.get("source_type", "Research Publication")
        ref_list.append(f"[{idx + 1}] {author_str} ({year}). \"{s.get('title')}\". *{journal}*. {f'DOI: {doi}' if doi else f'URL: {url}'}")

    formatted_refs = "\n".join(ref_list)

    # Word count expectations based on depth
    word_target = "1,200 - 1,800 words" if depth == "quick" else ("4,000 - 6,500 words" if depth == "deep" else "2,500 - 4,000 words")

    contract = state.get("contract", {})
    contract_header = ""
    if contract:
        contract_header = f"""
> **Research Contract Summary (as-of: {contract.get('as_of', '2026-10-08')})**  
> **Investigation Question:** {contract.get('question', query)}  
> **Decision Context:** {contract.get('decision_context', 'Academic literature synthesis')}  
> **Scope Boundaries:** {contract.get('scope', 'Peer-reviewed and preprint repositories')}  
> **Must-Resolve Subquestions:** {', '.join(contract.get('must_resolve', []))}  
"""

    # Build compact token-efficient ledger representation to avoid provider TPM exhaustion
    compact_ledger = []
    for e in evidence_matrix[:12]:
        ev_items = e.get("evidence", [])
        passage = ev_items[0].get("passage", "")[:180] if ev_items else e.get("quantitative_metric", "")[:180]
        compact_ledger.append({
            "claim_id": e.get("claim_id"),
            "claim": e.get("claim"),
            "status": e.get("status", "unverified"),
            "evidence_passage": passage,
            "source_indices": e.get("supporting_source_indices", [1]),
            "author_year": e.get("primary_author_year"),
            "open_question": e.get("open_question", ""),
        })

    prompt = f"""Topic: "{query}"
Depth Level: {depth.upper()} (Target Length: {word_target})
Citation Style: {citation_style.upper()}
Language: {"Indonesian (Formal Academic)" if language == "id" else "English (Formal Academic)"}

RESEARCH CONTRACT:
{json.dumps(contract, indent=2)}

---
VERIFIED EVIDENCE LEDGER (Center of Truth — Write ONLY what this ledger supports):
{json.dumps(compact_ledger, indent=2)}

---
AUDIT VERDICT & CONTRADICTIONS:
{json.dumps(verification_report, indent=2)}

---
BIBLIOGRAPHIC REPOSITORY ({len(sources)} validated sources):
{formatted_refs}

Authoring Directives (Research Machine Specification):
1. Include the Research Contract blockquote directly after the Title and before the Abstract.
2. In Section 3 (Evidence Synthesis), cite claims using bracketed numbers `[N]` directly corresponding to the Bibliographic Repository.
3. In Section 4, generate an informative Markdown Comparative Benchmark Table comparing key methodologies, empirical metrics, and findings.
4. In Section 5 (Critical Analysis, Contradictions & Limitations):
   - Explicitly detail any contested evidence or methodological divergences identified in the Evidence Ledger.
   - Do NOT silently average conflicting sources: explain where their experimental setups, sample distributions, or assumptions disagree.
5. In Section 6, explicitly list open questions and what the published evidence DOES NOT settle.
6. Ensure tone is educational, conservative, rigorous, and fully grounded."""

    llm = create_llm(
        provider=state.get("provider"),
        model=state.get("model"),
        api_key=state.get("api_key"),
        auth_type=state.get("auth_type", "api_key"),
        base_url=state.get("base_url"),
        temperature=0.15,
    )

    messages = [
        SystemMessage(content=WRITER_SYSTEM),
        HumanMessage(content=prompt),
    ]

    try:
        response = await llm.ainvoke(messages)
        content = response.content
        if isinstance(content, list):
            draft = " ".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content])
        else:
            draft = str(content)
    except Exception as exc:
        logger.error("writer_invocation_failed", error_type=type(exc).__name__)
        raise RuntimeError("The writing provider did not complete the report.") from None
    if not draft.strip():
        raise RuntimeError("The writing provider returned an empty report.")

    step_log = {
        "node": "writer",
        "title": "Scholarly Monograph Composed",
        "detail": f"Generated academic monograph ({len(draft.split())} words) with comparative evidence table and citations.",
        "word_count": len(draft.split()),
        "citations_indexed": len(ref_list),
    }

    logger.info("writer_completed", job_id=state.get("job_id"), words=len(draft.split()))
    return {
        "draft": draft,
        "status": "reviewing",
        "step_logs": state.get("step_logs", []) + [step_log],
    }
