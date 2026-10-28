"""Researcher agent node — gathers academic literature and empirical data across scientific repositories."""
from __future__ import annotations
import asyncio
import structlog
from src.agents.state import AgentState
from src.agents.tools import crossref_search, arxiv_search, pubmed_search, tavily_search

logger = structlog.get_logger()


async def researcher_node(state: AgentState) -> dict:
    """Execute research tasks across ArXiv, PubMed, CrossRef, and Web."""
    plan = state.get("plan", [])
    existing_sources = list(state.get("sources", []))
    seen_urls = {s.get("url") for s in existing_sources if s.get("url")}
    seen_dois = {s.get("doi") for s in existing_sources if s.get("doi")}
    seen_titles = {s.get("title", "").lower().strip() for s in existing_sources if s.get("title")}

    new_sources = []
    engine_stats = {"crossref": 0, "arxiv": 0, "pubmed": 0, "web": 0}

    from datetime import date
    current_date = date.today().isoformat()

    # Targeted search handling:
    # If the verifier or reviewer identified unverified or contested claims,
    # generate laser-targeted search queries specifically for those claims.
    tasks_to_run = list(plan)
    contested_claims = state.get("contested_claims", [])
    unverified_claims = state.get("unverified_claims", [])
    gap_analysis = state.get("gap_analysis")

    if unverified_claims:
        for u in unverified_claims[:2]:
            claim_text = u.get("claim", str(u)) if isinstance(u, dict) else str(u)
            tasks_to_run.insert(0, {
                "lane": "primary",
                "title": f"Resolve Unverified Claim: {claim_text[:40]}...",
                "search_query": f"{state['query']} {claim_text[:60]}",
                "target_engine": "crossref",
                "rationale": "Directly fetch primary empirical proof for unverified claim",
            })
    elif contested_claims:
        for c in contested_claims[:2]:
            conflict_text = c.get("conflict", str(c)) if isinstance(c, dict) else str(c)
            tasks_to_run.insert(0, {
                "lane": "counter",
                "title": f"Investigate Methodological Conflict: {conflict_text[:40]}...",
                "search_query": f"{state['query']} {conflict_text[:60]} methodology comparison",
                "target_engine": "crossref",
                "rationale": "Compare contradictory empirical study designs and sample populations",
            })
    elif gap_analysis:
        tasks_to_run.insert(0, {
            "lane": "independent",
            "title": "Address Academic Reviewer Gaps",
            "search_query": f"{state['query']} {gap_analysis[:80]}",
            "target_engine": "crossref",
            "rationale": "Directly address methodological gaps identified during peer review",
        })

    depth = state.get("depth", "standard")
    per_task_limit = 4 if depth == "quick" else (8 if depth == "deep" else 6)

    source_budget = state.get("sources_limit", 20)
    semaphore = asyncio.Semaphore(3)

    async def retrieve(task):
        async with semaphore:
            return await execute_search(task)

    async def execute_search(task):
        query = task.get("search_query", state["query"])
        target_engine = task.get("target_engine", "crossref")
        lane = task.get("lane", "primary")

        results = []
        try:
            if target_engine == "pubmed" and state.get("include_academic", True):
                results = await pubmed_search(query, max_results=per_task_limit)
                if not results:
                    results = await crossref_search(query, max_results=per_task_limit)
            elif target_engine == "arxiv" and state.get("include_academic", True):
                results = await arxiv_search(query, max_results=per_task_limit)
                if not results:
                    results = await crossref_search(query, max_results=per_task_limit)
            elif target_engine == "crossref" and state.get("include_academic", True):
                results = await crossref_search(query, max_results=per_task_limit)
            else:
                if state.get("include_web", True):
                    results = await tavily_search(query, max_results=per_task_limit)
                if not results and state.get("include_academic", True):
                    results = await crossref_search(query, max_results=per_task_limit)
        except Exception as e:
            logger.warning("vector_search_failed", engine=target_engine, error=type(e).__name__)
            # Fallback to crossref
            try:
                results = await crossref_search(query, max_results=per_task_limit) if state.get("include_academic", True) else []
            except Exception:
                results = []

        return task, results

    batches = await asyncio.gather(*(retrieve(task) for task in tasks_to_run[:12])) if len(existing_sources) < source_budget else []
    # Round-robin across search vectors prevents the first engine/lane from
    # consuming the entire source budget before counter-evidence is considered.
    interleaved = []
    for index in range(per_task_limit):
        for task, results in batches:
            if index < len(results):
                interleaved.append((task, results[index]))
    for task, result in interleaved:
        lane = task.get("lane", "primary")
        results = [result]
        # Deduplicate, format with immutable ID, and record exact passage
        for r in results:
            if len(existing_sources) + len(new_sources) >= source_budget:
                break
            url = r.get("url", "")
            doi = r.get("doi", "")
            title = r.get("title", "").lower().strip()

            if (url and url in seen_urls) or (doi and doi in seen_dois) or (title and title in seen_titles):
                continue

            if url:
                seen_urls.add(url)
            if doi:
                seen_dois.add(doi)
            if title:
                seen_titles.add(title)

            # Assign immutable Source ID (S-01, S-02, ...)
            source_id = f"S-{len(existing_sources) + len(new_sources) + 1:02d}"
            r["source_id"] = source_id
            r["accessed_at"] = current_date
            r["lane"] = lane
            # Ensure exact passage is present
            if not r.get("passage"):
                r["passage"] = r.get("snippet", "")[:800]

            new_sources.append(r)
            stype = r.get("source_type", "web")
            if stype in engine_stats:
                engine_stats[stype] += 1
            else:
                engine_stats["web"] += 1

    all_sources = existing_sources + new_sources
    if not all_sources:
        raise RuntimeError("No usable sources were retrieved. Revise the question or source settings.")
    logger.info(
        "researcher_completed",
        job_id=state.get("job_id"),
        new_sources=len(new_sources),
        total_sources=len(all_sources),
        stats=engine_stats,
    )

    step_log = {
        "node": "researcher",
        "title": "Empirical & Academic Evidence Retrieved",
        "detail": f"Gathered {len(all_sources)} retrieved sources across functional search lanes.",
        "stats": engine_stats,
        "sample_sources": [
            {
                "id": s.get("source_id"),
                "title": s.get("title"),
                "lane": s.get("lane"),
                "doi": s.get("doi"),
                "authors": s.get("authors", [])[:2],
                "year": s.get("published_date"),
            }
            for s in all_sources[:5]
        ],
    }

    return {
        "sources": all_sources,
        "status": "verifying",
        "step_logs": state.get("step_logs", []) + [step_log],
        "current_iteration": state.get("current_iteration", 0) + 1,
    }
