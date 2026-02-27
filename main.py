import sys
import os
import argparse
import logging
from typing import List
from dotenv import load_dotenv

from fetcher import fetch_arxiv_papers
from ranker import score_paper, PaperMetrics
from processor import process_paper, load_history, save_history, check_history
from llm_factory import LLMFactory
from paper_data import Paper
from semantic_fetcher import fetch_semantic_papers

# Configure Logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

def display_ranked_papers(scored_papers: List[tuple], limit: int):
    """
    Displays the top-ranked papers with their scores and rationale.
    """
    print("\n" + "="*80)
    print(f"RANKED PAPERS (Top {limit})")
    print("="*80)
    
    scored_papers.sort(key=lambda x: x[1].total_score, reverse=True)
    
    # We return top limit
    top_papers = scored_papers[:limit]
    
    for idx, (paper, metrics) in enumerate(top_papers):
        pub_date = paper.published.strftime("%Y%m%d")
        print(f"{idx + 1}. [{pub_date}] [Score: {metrics.total_score}/100] ")
        print(f"   Metrics: Breakthrough: {metrics.breakthrough_potential}, Utility: {metrics.practical_utility}, Novelty: {metrics.novelty}")
        print(f"            Impact: {metrics.scientific_impact}, Access: {metrics.layman_accessibility}, Code: {metrics.code_data_availability}")
        print(f"**{paper.title}**")
        print(f"   Rationale: {metrics.rationale}")
        print("-" * 80)
    
    return top_papers

def fetch_and_score(args, llm_factory, offset):
    fetch_limit = args.limit * 3
    print(f"\nFetching up to {fetch_limit} candidates from {args.source} for query '{args.category}' within last {args.days} days (Offset: {offset})...")
    
    if args.source == "semanticscholar":
        papers = fetch_semantic_papers(args.category, days=args.days, max_results=fetch_limit, offset=offset)
    else:
        if args.days > 60 and args.order == "descending":
            print("Note: 'arxiv' source may bias towards recent papers for long periods.")
            print("      Consider '--source semanticscholar' for impact-based ranking.")
        papers = fetch_arxiv_papers(args.category, days=args.days, max_results=fetch_limit, offset=offset, sort_order=args.order)
    
    if not papers:
        print("No papers found in this batch.")
        return []

    print(f"Found {len(papers)} papers. Ranking them now using {args.model}...")
    
    scored_batch = []
    for paper in papers:
        try:
            metrics = score_paper(paper.title, paper.summary, llm_factory)
            scored_batch.append((paper, metrics))
        except Exception as e:
            logger.error(f"Failed to score paper {paper.title}: {e}")
            
    return scored_batch

def main():
    parser = argparse.ArgumentParser(description="ArxivGnosis")
    parser.add_argument("--category", type=str, default="cs.AI", help="Arxiv category (e.g., cs.AI) or search query")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look back")
    parser.add_argument("--limit", type=int, default=10, help="Limit number of papers to fetch and rank")
    parser.add_argument("--provider", type=str, default="ollama", choices=["gemini", "openai", "anthropic", "ollama"], help="LLM Provider")
    parser.add_argument("--model", type=str, default="ollama/qwen2.5:7b", help="LLM Model Name")
    parser.add_argument("--source", type=str, default="arxiv", choices=["arxiv", "semanticscholar"], help="Source for papers: 'arxiv' (recent) or 'semanticscholar' (best/most cited)")
    parser.add_argument("--min_score", type=int, default=60, help="Minimum score threshold. If top papers are below this, user is prompted to iterate.")
    parser.add_argument("--order", type=str, default="ascending", choices=["descending", "ascending"], help="Sort order for Arxiv papers (descending=newest first, ascending=oldest first).")

    args = parser.parse_args()
    
    # Initialize LLM Factory
    try:
        print(f"Initializing LLM: {args.provider} / {args.model}")
        if args.provider == "ollama":
             print("Note: Ensure Ollama is running ('ollama serve') and the model is pulled.")
        llm_factory = LLMFactory(provider=args.provider, model_name=args.model)
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        return

    offset = 0
    all_scored_papers = []
    
    # ---------------------------------------------------------
    # Phase 1: Initial Fetching Loop (Automatic based on Score)
    # ---------------------------------------------------------
    while True:
        batch = fetch_and_score(args, llm_factory, offset)
        if not batch:
            if not all_scored_papers:
                print("No papers found matching criteria.")
                return
            else:
                print("No more papers found.")
                break
        
        all_scored_papers.extend(batch)
        all_scored_papers.sort(key=lambda x: x[1].total_score, reverse=True)
        
        # Check if we satisfy min_score
        top_score = all_scored_papers[0][1].total_score
        
        if args.min_score > 0 and top_score < args.min_score:
            print(f"\nTop score found so far ({top_score}) is below minimum threshold ({args.min_score}).")
            choice = input(f"Iterate to next batch of {args.limit * 3} candidates? (y/n) [y]: ").strip().lower()
            if choice == '' or choice == 'y':
                offset += args.limit * 3
                continue
            else:
                print("Selecting from existing papers regardless of score.")
                break
        else:
            # Score met or no min_score set
            break

    # ---------------------------------------------------------
    # Phase 2: Display & Selection Loop (With Manual Iterate)
    # ---------------------------------------------------------
    while True:
        if not all_scored_papers:
            print("No papers available.")
            return

        # Display Top N from ALL accumulated papers
        top_papers = display_ranked_papers(all_scored_papers, args.limit)
            
        try:
            selection = input("\nEnter paper numbers (e.g., '1', '1-3'), 'i' to iterate (fetch more), or 'q' to quit: ")
            
            if selection.lower() == 'q':
                break
            
            if selection.lower() == 'i':
                offset += args.limit * 3
                batch = fetch_and_score(args, llm_factory, offset)
                if batch:
                    all_scored_papers.extend(batch)
                    # Loop back to top of while to re-display sorted list
                    continue 
                else:
                    print("No more papers found.")
                    continue

            indices = set()
            parts = [s.strip() for s in selection.split(',')]
            
            valid_parts = True
            for part in parts:
                if '-' in part:
                    try:
                        start, end = map(int, part.split('-'))
                        indices.update(range(start - 1, end))
                    except ValueError:
                        valid_parts = False; break
                elif part.isdigit():
                    indices.add(int(part) - 1)
                else:
                    valid_parts = False; break
            
            if not valid_parts:
                print("Invalid input format.")
                continue
            
            valid_indices = sorted([i for i in indices if 0 <= i < len(top_papers)])

            if not valid_indices:
                print("No valid selections found.")
                continue
            
            print(f"Processing {len(valid_indices)} papers...")
            
            for idx in valid_indices:
                selected_paper, metrics = top_papers[idx]
                print(f"\nProcessing ({idx+1}/{len(top_papers)}): {selected_paper.title}")
                process_paper(selected_paper, llm_factory)
                
            cont = input("\nProcess more papers? (y/n): ")
            if cont.lower() != 'y':
                break
        except Exception as e:
            print(f"Error processing input: {e}")

if __name__ == "__main__":
    main()
