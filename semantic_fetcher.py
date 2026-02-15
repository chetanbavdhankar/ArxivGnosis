from semanticscholar import SemanticScholar
from datetime import datetime, timezone, timedelta
from typing import List
from paper_data import Paper
import logging

logger = logging.getLogger(__name__)

def fetch_semantic_papers(query: str, days: int = 365, max_results: int = 50, offset: int = 0) -> List[Paper]:
    """
    Fetches papers from Semantic Scholar, filters by date, and sorts by citation count.
    Focuses on 'arXiv' venue if possible or general search.
    """
    sch = SemanticScholar()
    
    # Calculate year range string (e.g., "2024-2025")
    today = datetime.now(timezone.utc)
    current_year = today.year
    start_date = today - timedelta(days=days)
    start_year = start_date.year
    
    year_range = f"{start_year}-{current_year}"
    search_query = query
    
    try:
        # Search
        # To support pagination for "Top Cited", we must fetch a larger pool and slice it.
        # Semantic Scholar API 'offset' parameter skips relevance-sorted results.
        # We want to sort by citation count.
        # So we fetch a large enough pool (offset + max_results), sort them all, and then take the slice.
        # This is an approximation but works for "Next Batch".
        
        pool_size = (max_results + offset) * 3
        fetch_limit = min(pool_size, 300) # Cap at 300 to avoid timeouts
        
        print(f"Querying Semantic Scholar for '{search_query}' (fetching up to {fetch_limit} candidates)...")
        
        results = sch.search_paper(
            search_query,
            year=year_range,
            fields=['title', 'abstract', 'citationCount', 'venue', 'publicationDate', 'url', 'externalIds', 'openAccessPdf'],
            limit=fetch_limit
        )
        
        print(f"Processing candidate papers...")
        
        papers = []
        for item in results:
            # Filter by specific date if needed (API filters by year only)
            if not item.publicationDate:
                continue
                
            try:
                # SemanticScholar might return None for some fields
                if item.publicationDate is None:
                    continue
                    
                pub_date = datetime.strptime(item.publicationDate, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except Exception as e:
                # date parsing err
                continue
                
            if pub_date < start_date:
                continue
            
            # Extract PDF URL
            pdf_url = None
            entry_id = item.paperId
            
            # 1. Try Arxiv
            if item.externalIds and 'ArXiv' in item.externalIds:
                entry_id = f"http://arxiv.org/abs/{item.externalIds['ArXiv']}"
                pdf_url = f"http://arxiv.org/pdf/{item.externalIds['ArXiv']}.pdf"
            # 2. Try Open Access PDF
            elif item.openAccessPdf and 'url' in item.openAccessPdf:
                pdf_url = item.openAccessPdf['url']
            # 3. Fallback to S2 URL (will be HTML, but better than nothing for entry_id)
            else:
                 pdf_url = item.url
            
            paper = Paper(
                title=item.title,
                summary=item.abstract if item.abstract else "No abstract available.",
                published=pub_date,
                pdf_url=pdf_url,
                entry_id=entry_id,
                citation_count=item.citationCount if item.citationCount else 0,
                source="semantic_scholar"
            )
            papers.append(paper)
            
        # Sort by citation count descending
        papers.sort(key=lambda x: x.citation_count, reverse=True)
        
        # Return slice based on offset
        # Note: If offset is beyond available papers, this returns empty list.
        start_idx = offset
        end_idx = offset + max_results
        return papers[start_idx:end_idx]
        
    except Exception as e:
        logger.error(f"Semantic Scholar Fetch Error: {e}")
        print(f"Error fetching from Semantic Scholar: {e}")
        return []

if __name__ == "__main__":
    # Test
    print("Fetching Top Cited Papers via Semantic Scholar...")
    papers = fetch_semantic_papers("cs.AI", days=365, max_results=5)
    for p in papers:
        print(f"[{p.citation_count} cites] {p.title} ({p.published.date()})")
