"""
ArxivGnosis Web Server
Flask API wrapping existing CLI pipeline into REST endpoints.
"""
import os
import sys
import json
import logging
import threading
import webbrowser
from datetime import datetime, timezone
from queue import Queue

from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from dotenv import load_dotenv

from fetcher import fetch_arxiv_papers
from semantic_fetcher import fetch_semantic_papers
from ranker import score_paper, PaperMetrics
from processor import process_paper
from llm_factory import LLMFactory
from paper_data import Paper

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# In-memory session state (single-user; extend with session IDs for multi-user)
state = {
    "all_scored_papers": [],   # List of dicts
    "offset": 0,
    "llm_factory": None,
    "last_params": {},
    "progress_queues": {},     # task_id -> Queue for SSE
}
state_lock = threading.Lock()


def paper_to_dict(paper: Paper, metrics: PaperMetrics, idx: int) -> dict:
    return {
        "index": idx,
        "title": paper.title,
        "summary": paper.summary[:300] + ("..." if len(paper.summary) > 300 else ""),
        "full_summary": paper.summary,
        "published": paper.published.strftime("%Y-%m-%d"),
        "pdf_url": paper.pdf_url or "",
        "entry_id": paper.entry_id,
        "citation_count": paper.citation_count,
        "source": paper.source,
        "metrics": {
            "breakthrough_potential": metrics.breakthrough_potential,
            "practical_utility": metrics.practical_utility,
            "scientific_impact": metrics.scientific_impact,
            "layman_accessibility": metrics.layman_accessibility,
            "novelty": metrics.novelty,
            "interdisciplinary_potential": metrics.interdisciplinary_potential,
            "code_data_availability": metrics.code_data_availability,
            "clarity_of_presentation": metrics.clarity_of_presentation,
            "social_relevance": metrics.social_relevance,
            "entertainment_value": metrics.entertainment_value,
            "total_score": metrics.total_score,
            "rationale": metrics.rationale,
        },
    }


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/api/fetch', methods=['POST'])
def api_fetch():
    """Fetch & score papers. Supports initial fetch and iterate (next batch)."""
    data = request.json or {}

    category = data.get("category", "cs.AI")
    days = int(data.get("days", 7))
    limit = int(data.get("limit", 10))
    provider = data.get("provider", "ollama")
    model = data.get("model", "ollama/qwen2.5:7b")
    source = data.get("source", "arxiv")
    order = data.get("order", "ascending")
    iterate = data.get("iterate", False)

    with state_lock:
        if iterate and state["llm_factory"]:
            llm_factory = state["llm_factory"]
            offset = state["offset"]
        else:
            # Fresh run — reset state
            try:
                llm_factory = LLMFactory(provider=provider, model_name=model)
            except Exception as e:
                return jsonify({"error": f"LLM init failed: {e}"}), 500
            state["llm_factory"] = llm_factory
            state["all_scored_papers"] = []
            state["offset"] = 0
            state["last_params"] = {
                "category": category, "days": days, "limit": limit,
                "source": source, "order": order, "provider": provider, "model": model,
            }
            offset = 0

    # Fetch papers
    fetch_limit = limit * 3
    try:
        if source == "semanticscholar":
            papers = fetch_semantic_papers(category, days=days, max_results=fetch_limit, offset=offset)
        else:
            papers = fetch_arxiv_papers(category, days=days, max_results=fetch_limit, offset=offset, sort_order=order)
    except Exception as e:
        return jsonify({"error": f"Fetch error: {e}"}), 500

    if not papers:
        with state_lock:
            existing = state["all_scored_papers"]
        if existing:
            return jsonify({"papers": existing, "message": "No more papers found.", "total": len(existing)})
        return jsonify({"papers": [], "message": "No papers found.", "total": 0})

    # Score papers
    scored_batch = []
    errors = []
    for i, paper in enumerate(papers):
        try:
            metrics = score_paper(paper.title, paper.summary, llm_factory)
            scored_batch.append(paper_to_dict(paper, metrics, 0))
        except Exception as e:
            errors.append(f"Failed to score '{paper.title[:40]}': {e}")
            logger.error(f"Score error: {e}")

    with state_lock:
        # Merge into global pool
        state["all_scored_papers"].extend(scored_batch)
        # Re-sort globally by total_score desc
        state["all_scored_papers"].sort(key=lambda x: x["metrics"]["total_score"], reverse=True)
        # Keep only the top 'limit'
        state["all_scored_papers"] = state["all_scored_papers"][:limit]
        # Re-index
        for i, p in enumerate(state["all_scored_papers"]):
            p["index"] = i
        state["offset"] = offset + fetch_limit
        result = state["all_scored_papers"]

    return jsonify({
        "papers": result,
        "total": len(result),
        "new_in_batch": len(scored_batch),
        "errors": errors,
        "message": f"Scored {len(scored_batch)} papers. Total pool: {len(result)}.",
    })


@app.route('/api/process', methods=['POST'])
def api_process():
    """Process selected papers — download PDF + generate summary."""
    data = request.json or {}
    indices = data.get("indices", [])

    with state_lock:
        llm_factory = state["llm_factory"]
        all_papers = state["all_scored_papers"]

    if not llm_factory:
        return jsonify({"error": "No active session. Run fetch first."}), 400

    results = []
    for idx in indices:
        if idx < 0 or idx >= len(all_papers):
            results.append({"index": idx, "status": "error", "message": "Invalid index"})
            continue

        paper_data = all_papers[idx]
        # Reconstruct Paper object
        paper = Paper(
            title=paper_data["title"],
            summary=paper_data["full_summary"],
            published=datetime.strptime(paper_data["published"], "%Y-%m-%d").replace(tzinfo=timezone.utc),
            pdf_url=paper_data["pdf_url"],
            entry_id=paper_data["entry_id"],
            citation_count=paper_data["citation_count"],
            source=paper_data["source"],
        )
        try:
            process_paper(paper, llm_factory)
            results.append({"index": idx, "status": "success", "title": paper.title})
        except Exception as e:
            results.append({"index": idx, "status": "error", "message": str(e), "title": paper.title})

    return jsonify({"results": results})


@app.route('/api/reset', methods=['POST'])
def api_reset():
    """Clear session state."""
    with state_lock:
        state["all_scored_papers"] = []
        state["offset"] = 0
        state["llm_factory"] = None
        state["last_params"] = {}
    return jsonify({"message": "Session reset."})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    url = f"http://localhost:{port}"
    print(f"\n  ArxivGnosis Web UI -> {url}\n")
    # Auto-open browser after a short delay to let Flask bind the port
    threading.Timer(1.25, webbrowser.open, args=[url]).start()
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
