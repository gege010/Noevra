import httpx
import time
import os

API_BASE = "http://localhost:8000/api/v1/research"

QUERIES = [
    "Impact of transformer architecture on modern NLP",
    "Comparison of RAG vs fine-tuning for domain-specific LLMs",
    "State of reinforcement learning from human feedback"
]

def run_research(query):
    print(f"\nStarting research: {query}")
    try:
        resp = httpx.post(API_BASE, json={"query": query, "depth": "standard", "max_iterations": 8}, timeout=10.0)
        resp.raise_for_status()
        job_id = resp.json()["job_id"]
        print(f"Job ID: {job_id}")
        
        while True:
            time.sleep(5)
            status_resp = httpx.get(f"{API_BASE}/{job_id}")
            if status_resp.status_code != 200:
                print(f"Error checking status: {status_resp.status_code}")
                continue
            
            data = status_resp.json()
            status = data["status"]
            print(f"Status: {status} ({data.get('progress_pct', 0)}%)")
            
            if status == "done":
                print(f"Trace URL: {data.get('trace_url')}")
                # Download report
                os.makedirs("data/reports/examples", exist_ok=True)
                report_resp = httpx.get(f"{API_BASE}/{job_id}/report")
                md_content = report_resp.json().get("report_markdown", "")
                
                safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in query)[:50]
                filename = f"data/reports/examples/{job_id[:8]}_{safe_title}.md"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(md_content)
                print(f"Saved: {filename}")
                break
            elif status == "failed":
                print(f"Failed: {data.get('error')}")
                break
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    for q in QUERIES:
        run_research(q)
