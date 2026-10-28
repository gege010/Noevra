"""Deterministic provenance checks; model agreement is not source verification."""
from __future__ import annotations


def validate_claim(item: dict, sources: list[dict], index: int, checked: str) -> dict:
    claim = dict(item)
    by_id = {s.get("source_id") or f"S-{i + 1:02d}": s for i, s in enumerate(sources)}
    evidence = []
    for entry in claim.get("evidence", []):
        if not isinstance(entry, dict):
            continue
        source = by_id.get(entry.get("source_id"))
        passage = entry.get("passage", "")
        original = (source.get("passage") or source.get("snippet") or "") if source else ""
        if not source or not isinstance(passage, str) or not passage.strip():
            continue
        if " ".join(passage.split()) not in " ".join(original.split()):
            continue
        evidence.append({**entry, "url": source.get("url", ""),
                         "publisher": source.get("journal", source.get("source_type", "")),
                         "accessed_at": source.get("accessed_at", checked)})
    claim.update(claim_id=f"C-{index + 1:02d}", evidence=evidence, last_checked=checked)
    status = claim.get("status", "unverified")
    if status not in {"supported", "contested", "unverified", "stale"}:
        status = "unverified"
    if status in {"supported", "contested"} and not evidence:
        status = "unverified"
        claim["reason"] = "No exact passage could be matched to the retrieved source corpus."
    if status == "supported" and not any(e.get("stance") == "supports" for e in evidence):
        status = "unverified"
    claim["status"] = status
    claim.setdefault("open_question", "")
    return claim
