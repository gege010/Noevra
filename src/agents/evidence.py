"""Deterministic provenance checks; model agreement is not source verification."""

from __future__ import annotations


def validate_claim(item: dict, sources: list[dict], index: int, checked: str) -> dict:
    claim = dict(item)
    by_id = {s.get("source_id") or f"S-{i + 1:02d}": s for i, s in enumerate(sources)}
    evidence = []
    entries = claim.get("evidence", [])
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict) or not isinstance(entry.get("source_id"), str):
            continue
        source = by_id.get(entry.get("source_id"))
        passage = entry.get("passage", "")
        original = (source.get("passage") or source.get("snippet") or "") if source else ""
        if not source or not isinstance(passage, str) or not passage.strip():
            continue
        if " ".join(passage.split()) not in " ".join(original.split()):
            continue
        evidence.append(
            {
                **entry,
                "url": source.get("url", ""),
                "source_type": source.get("source_type", "web"),
                "published_at": source.get("published_date", ""),
                "publisher": source.get("journal", source.get("source_type", "")),
                "accessed_at": source.get("accessed_at", checked),
            }
        )
    claim.update(claim_id=f"C-{index + 1:02d}", evidence=evidence, last_checked=checked)
    status = claim.get("status", "unverified")
    if not isinstance(status, str) or status not in {
        "supported",
        "contested",
        "unverified",
        "stale",
    }:
        status = "unverified"
    if status in {"supported", "contested"} and not evidence:
        status = "unverified"
        claim["reason"] = "No exact passage could be matched to the retrieved source corpus."
    if status == "supported" and not any(e.get("stance") == "supports" for e in evidence):
        status = "unverified"
    if status == "contested":
        supporters = {e["source_id"] for e in evidence if e.get("stance") == "supports"}
        weakeners = {e["source_id"] for e in evidence if e.get("stance") == "weakens"}
        if not supporters or not weakeners or len(supporters | weakeners) < 2:
            status = "unverified"
            claim["reason"] = (
                "A contested claim requires matching supporting and weakening passages from distinct retrieved sources."
            )
    indices = {key: i + 1 for i, key in enumerate(by_id)}
    claim["supporting_source_indices"] = sorted({indices[e["source_id"]] for e in evidence})
    claim["status"] = status
    claim.setdefault("open_question", "")
    return claim
