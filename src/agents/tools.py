"""Multi-source tool definitions for scientific research and verification."""
from __future__ import annotations
import asyncio
import re
from typing import Any
import httpx
import structlog
from bs4 import BeautifulSoup
from src.config import get_settings
from src.exceptions.handlers import TavilyRateLimitError, ArxivAPIError, APIError

logger = structlog.get_logger()
settings = get_settings()


def _sanitize_html(raw: str) -> str:
    """Strip HTML tags, clean text, and neutralize adversarial prompt injection in untrusted web data."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", raw, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    # Neutralize prompt injection directives in untrusted retrieved documents
    text = re.sub(r"(?i)(ignore\s+(all\s+)?previous\s+instructions|system\s+prompt\s*:|you\s+must\s+now\s+act\s+as)", "[UNTRUSTED_INSTRUCTION_FILTERED]", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:10_000]


async def crossref_search(query: str, max_results: int = 8) -> list[dict]:
    """
    Search millions of peer-reviewed scientific journal articles via CrossRef REST API.
    Covers IEEE, Nature, Springer, Elsevier, Wiley, ACM, PLOS, etc.
    No API key required.
    """
    try:
        async with httpx.AsyncClient(headers={"User-Agent": "MultiAgentResearchAssistant/2.0 (mailto:academic-research@deepmind.edu)"}) as client:
            resp = await client.get(
                "https://api.crossref.org/works",
                params={"query": query, "rows": min(max_results, 15), "sort": "relevance"},
                timeout=20.0,
            )
            if resp.status_code != 200:
                logger.warning("crossref_api_error", status=resp.status_code)
                return []

            data = resp.json()
            items = data.get("message", {}).get("items", [])
            results = []
            for item in items:
                title = " ".join(item.get("title", []))
                if not title:
                    continue
                # Extract author names
                authors = []
                for author in item.get("author", []):
                    given = author.get("given", "")
                    family = author.get("family", "")
                    name = f"{given} {family}".strip()
                    if name:
                        authors.append(name)

                # Extract publication year
                year = ""
                pub_parts = item.get("published", {}).get("date-parts", [[]])[0]
                if pub_parts:
                    year = str(pub_parts[0])

                doi = item.get("DOI", "")
                url = item.get("URL", f"https://doi.org/{doi}" if doi else "")
                journal = item.get("container-title", [""])[0] if item.get("container-title") else ""
                abstract = item.get("abstract", "")
                if abstract:
                    abstract = re.sub(r"<[^>]+>", "", abstract).strip()

                snippet = abstract[:500] if abstract else f"Published in {journal} ({year}). DOI: {doi}"

                results.append({
                    "title": title,
                    "snippet": snippet,
                    "url": url,
                    "doi": doi,
                    "authors": authors[:5],
                    "published_date": year,
                    "journal": journal,
                    "citation_count": item.get("is-referenced-by-count", 0),
                    "source_type": "journal",
                    "relevance_score": 0.85,
                })
            logger.info("crossref_search_done", query=query, results_count=len(results))
            return results
    except Exception as exc:
        logger.warning("crossref_search_failed", query=query, error=str(exc))
        return []


async def pubmed_search(query: str, max_results: int = 6) -> list[dict]:
    """
    Search PubMed/NCBI for biomedical, clinical, pharmacology, and life sciences studies.
    No API key required.
    """
    try:
        async with httpx.AsyncClient() as client:
            # 1. Search for PMIDs
            esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            resp = await client.get(
                esearch_url,
                params={"db": "pubmed", "term": query, "retmode": "json", "retmax": min(max_results, 10)},
                timeout=15.0,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            id_list = data.get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return []

            # 2. Fetch paper summaries
            esummary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            summary_resp = await client.get(
                esummary_url,
                params={"db": "pubmed", "id": ",".join(id_list), "retmode": "json"},
                timeout=15.0,
            )
            if summary_resp.status_code != 200:
                return []

            sum_data = summary_resp.json().get("result", {})
            results = []
            for pmid in id_list:
                item = sum_data.get(pmid)
                if not item:
                    continue
                title = item.get("title", "").strip().rstrip(".")
                pubdate = item.get("pubdate", "")
                authors = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]
                source = item.get("source", "")
                doi = ""
                for article_id in item.get("articleids", []):
                    if article_id.get("idtype") == "doi":
                        doi = article_id.get("value")
                        break

                url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                results.append({
                    "title": title,
                    "snippet": f"PubMed Study (PMID: {pmid}). Journal: {source} ({pubdate}).",
                    "url": url,
                    "pmid": pmid,
                    "doi": doi,
                    "authors": authors[:5],
                    "published_date": pubdate[:4],
                    "journal": source,
                    "source_type": "pubmed",
                    "relevance_score": 0.9,
                })
            logger.info("pubmed_search_done", query=query, results_count=len(results))
            return results
    except Exception as exc:
        logger.warning("pubmed_search_failed", query=query, error=str(exc))
        return []


def _parse_arxiv_atom(xml_text: str) -> list[dict]:
    """Parse ArXiv Atom XML feed into dict list."""
    results = []
    entries = re.findall(r"<entry>(.*?)</entry>", xml_text, re.DOTALL)
    for entry in entries:
        title = re.search(r"<title>(.*?)</title>", entry, re.DOTALL)
        summary = re.search(r"<summary>(.*?)</summary>", entry, re.DOTALL)
        authors = re.findall(r"<name>(.*?)</name>", entry)
        link = re.search(r"<id>(.*?)</id>", entry)
        published = re.search(r"<published>(.*?)</published>", entry)
        arxiv_id_match = re.search(r"arxiv.org/abs/([^\s]+)", entry)
        results.append({
            "title": (title.group(1).strip().replace("\n", " ") if title else "Unknown"),
            "snippet": (summary.group(1).strip().replace("\n", " ") if summary else "")[:600],
            "url": link.group(1).strip() if link else "",
            "arxiv_id": arxiv_id_match.group(1) if arxiv_id_match else "",
            "authors": [a.strip() for a in authors],
            "published_date": (published.group(1)[:10] if published else ""),
            "source_type": "arxiv",
            "relevance_score": 0.8,
        })
    return results


async def arxiv_search(query: str, max_results: int = 8) -> list[dict]:
    """
    Search ArXiv for preprints across Computer Science, AI, Physics, Math, Quantitative Biology.
    """
    await asyncio.sleep(1.0)
    try:
        async with httpx.AsyncClient() as client:
            search_url = (
                f"https://export.arxiv.org/api/query"
                f"?search_query=all:{query}"
                f"&start=0"
                f"&max_results={min(max_results, 30)}"
                f"&sortBy=relevance"
            )
            resp = await client.get(search_url, timeout=25.0)
            if resp.status_code != 200:
                raise ArxivAPIError(f"ArXiv API error: {resp.status_code}")
            results = _parse_arxiv_atom(resp.text)
            logger.info("arxiv_search_done", query=query, results_count=len(results))
            return results
    except ArxivAPIError:
        raise
    except Exception as exc:
        logger.warning("arxiv_search_failed", query=query, error=str(exc))
        return []


async def tavily_search(query: str, max_results: int = 10) -> list[dict]:
    """
    Search the web and news using Tavily API.
    """
    if not settings.tavily_api_key:
        logger.warning("tavily_api_key_not_configured_falling_back")
        return await open_web_search(query, max_results=max_results)

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.tavily_api_key,
                    "query": query,
                    "max_results": min(max_results, 20),
                    "include_answer": False,
                    "include_raw_content": False,
                },
                timeout=25.0,
            )
            if resp.status_code == 429:
                logger.warning("tavily_rate_limit_exceeded")
                raise TavilyRateLimitError("Tavily search rate limit reached.")
            if resp.status_code != 200:
                logger.warning(f"tavily_api_error_{resp.status_code}_falling_back")
                return await open_web_search(query, max_results=max_results)
            data = resp.json()
            results = data.get("results", [])
            logger.info("tavily_search_done", query=query, results_count=len(results))
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", ""),
                    "source_type": "web",
                    "relevance_score": 0.7,
                }
                for r in results
            ]
    except TavilyRateLimitError:
        raise
    except Exception as exc:
        logger.warning("tavily_search_failed_falling_back", query=query, error=str(exc))
        return await open_web_search(query, max_results=max_results)


async def open_web_search(query: str, max_results: int = 6) -> list[dict]:
    """
    Zero-key open scientific fallback search via Wikipedia API and open web endpoints.
    """
    results = []
    try:
        async with httpx.AsyncClient() as client:
            wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&format=json&utf8=1&srlimit={min(max_results, 5)}"
            resp = await client.get(wiki_url, timeout=12.0)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("query", {}).get("search", []):
                    title = item.get("title", "")
                    clean_snippet = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
                    page_id = item.get("pageid", "")
                    results.append({
                        "title": f"Wikipedia: {title}",
                        "snippet": clean_snippet,
                        "url": f"https://en.wikipedia.org/?curid={page_id}",
                        "source_type": "encyclopedia",
                        "relevance_score": 0.65,
                    })
    except Exception as exc:
        logger.warning("open_web_search_failed", query=query, error=str(exc))
    return results


async def web_fetch(url: str) -> str:
    """
    Fetch and extract clean text from a URL using BeautifulSoup.
    """
    try:
        async with httpx.AsyncClient(follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (Academic Research Assistant)"}) as client:
            resp = await client.get(url, timeout=20.0)
            if resp.status_code in (403, 404):
                return ""
            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                return ""
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                tag.extract()
            text = " ".join(soup.stripped_strings)
            return text[:10_000]
    except Exception as exc:
        logger.warning("web_fetch_failed", url=url, error=str(exc))
        return ""


async def read_document(url_or_path: str) -> str:
    """Read document text (URL or file)."""
    if url_or_path.startswith("http"):
        return await web_fetch(url_or_path)
    try:
        with open(url_or_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()[:10_000]
    except Exception as exc:
        return f"Error reading document: {exc}"


def execute_code(code: str) -> str:
    """Execute Python code for statistical calculations or data verification."""
    try:
        from langchain_experimental.utilities import PythonREPL
        repl = PythonREPL()
        result = repl.run(code)
        return result if result else "Code executed successfully with no output."
    except Exception as exc:
        return f"Execution Error: {str(exc)}"
