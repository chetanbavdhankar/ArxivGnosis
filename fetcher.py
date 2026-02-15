import arxiv
import datetime
import logging
from typing import List, Optional
from paper_data import Paper

logger = logging.getLogger(__name__)

class CategoryMapper:
    """
    Maps natural language terms to Arxiv category codes.
    """
    
    # Static mapping of common terms to categories
    # This is a curated list based on Arxiv taxonomy
    CATEGORY_MAP = {
        # Computer Science
        "ai": "cs.AI",
        "artificial intelligence": "cs.AI",
        "computer vision": "cs.CV",
        "vision": "cs.CV",
        "cv": "cs.CV",
        "nlp": "cs.CL",
        "natural language processing": "cs.CL",
        "language": "cs.CL",
        "cl": "cs.CL",
        "ml": "cs.LG",
        "machine learning": "cs.LG",
        "learning": "cs.LG",
        "robotics": "cs.RO",
        "robot": "cs.RO",
        "graphics": "cs.GR",
        "hci": "cs.HC",
        "human computer interaction": "cs.HC",
        "security": "cs.CR",
        "crypto": "cs.CR",
        "cryptography": "cs.CR",
        "networks": "cs.NI",
        "networking": "cs.NI",
        "architecture": "cs.AR",
        "hardware": "cs.AR",
        "distributed": "cs.DC",
        "parallel": "cs.DC",
        "databases": "cs.DB",
        "data structures": "cs.DS",
        "algorithms": "cs.DS",
        "se": "cs.SE",
        "software engineering": "cs.SE",
        "game theory": "cs.GT",
        
        # Physics - Astrophysics
        "astrophysics": "astro-ph", # Will be effectively astro-ph*
        "astro": "astro-ph",
        "cosmology": "astro-ph.CO",
        "galaxies": "astro-ph.GA",
        "planets": "astro-ph.EP",
        "earth": "astro-ph.EP",
        "high energy astro": "astro-ph.HE",
        "solar": "astro-ph.SR",
        
        # Physics - Condensed Matter
        "condensed matter": "cond-mat",
        "materials": "cond-mat.mtrl-sci",
        "superconductivity": "cond-mat.supr-con",
        "quantum gases": "cond-mat.quant-gas",
        "statistical mechanics": "cond-mat.stat-mech",
        "soft matter": "cond-mat.soft",
        
        # Physics - High Energy
        "hep": "hep-th", # Defaulting to theory if unsure
        "high energy physics": "hep-th",
        "hep-th": "hep-th",
        "hep-ph": "hep-ph",
        "hep-ex": "hep-ex",
        "lattice": "hep-lat",
        
        # Physics - Quantum
        "quantum": "quant-ph",
        "quantum physics": "quant-ph",
        "quantum computing": "quant-ph",
        "quant-ph": "quant-ph",
        
        # Physics - General
        "physics": "physics",
        "relativity": "gr-qc",
        "gravity": "gr-qc",
        "gr": "gr-qc",
        
        # Mathematics
        "math": "math",
        "mathematics": "math",
        "algebra": "math.AC",
        "analysis": "math.FA", # Functional Analysis mostly
        "geometry": "math.DG",
        "probability": "math.PR",
        "statistics": "stat.TH",
        
        # Stats
        "stat": "stat",
        "stats": "stat",
        "statistics (gen)": "stat",
        
        # EESS
        "audio": "eess.AS",
        "signal processing": "eess.SP",
        "image processing": "eess.IV",
        
        # Quantitative Finance
        "finance": "q-fin",
        "pricing": "q-fin.PR",
        "economics": "econ",
    }
    
    @staticmethod
    def get_code(user_input: str) -> str:
        """
        Returns the Arxiv category code for a given input.
        If no direct map found, returns the input normalized.
        """
        normalized = user_input.lower().strip()
        
        # Check explicit map
        if normalized in CategoryMapper.CATEGORY_MAP:
            return CategoryMapper.CATEGORY_MAP[normalized]
        
        # Check if it looks like a valid code already (e.g. cs.AI)
        # Simple heuristic: contains dot or hyphen, short length
        if ('.' in normalized or '-' in normalized) and len(normalized) < 20:
             return normalized
             
        # If simplistic, might be a top level category like 'cs' key not in map? 
        # (Though we added 'cs' as explicit key? No, adding now)
        if normalized in ['cs', 'math', 'stat', 'econ', 'q-bio', 'q-fin']:
            return normalized

        return normalized

def fetch_arxiv_papers(category: str, days: int = 7, max_results: int = 50, offset: int = 0, sort_order: str = "descending") -> List[Paper]:
    """
    Fetches papers from Arxiv for a specific category within the last X days.
    """
    
    # Map user input to category code
    category_code = CategoryMapper.get_code(category)
    
    # Calculate date range
    today = datetime.datetime.now(datetime.timezone.utc)
    start_date = today - datetime.timedelta(days=days)
    
    # Construct query
    
    # Logic:
    # 1. If it looks like a category code (has . or - or is top level), use `cat:`
    # 2. Otherwise, treat as a search keyword `all:`
    
    is_category_code = any(x in category_code for x in ['.', '-']) or category_code in ['cs', 'math', 'physics', 'stat', 'econ', 'q-bio', 'q-fin']
    
    if is_category_code:
        # Auto-append wildcard for top-level categories if no sub-category and no wildcard
        if '.' not in category_code and '*' not in category_code and ' ' not in category_code:
             print(f"Refining query: '{category}' -> category '{category_code}*' (includes subcategories)")
             query = f'cat:{category_code}*'
        else:
             print(f"Using category query: '{category_code}'")
             query = f'cat:{category_code}'
    else:
        # Treat as search keyword
        print(f"Refining query: '{category}' -> search keyword 'all:{category}'")
        query = f'all:{category}'
    
    client = arxiv.Client(
        page_size=50,
        delay_seconds=3.0,
        num_retries=3
    )
    
    # Note: arxiv.Search doesn't support offset directly in all versions, 
    # but client.results generator allows skipping.
    # However, to be efficient, we want the API to fetch the correct page.
    # arxiv library wraps standard API which supports start=...
    # But wrapper seems to hide it in favor of generator?
    # Actually, legacy API supports start. Wrapper might not.
    # Approach: Ask for max_results + offset, and slice locally? No, expensive.
    # Better: Use generator skipping.
    
    # Determine Sort Criteria
    # If using Keywords + Long Range, prioritize Relevance for API fetch.
    # Otherwise, stick to SubmittedDate.
    sort_by = arxiv.SortCriterion.SubmittedDate
    if not is_category_code and days > 60:
         print("Large date range + Keyword search detected: Sorting by Relevance for API fetch.")
         sort_by = arxiv.SortCriterion.Relevance
    
    # API Sort Order: 
    # CRITICAL FIX: We must ALWAYS fetch Descending (Newest/Best) from API to get papers
    # in the recent window (last X days).
    # If we fetch Ascending, we get papers from 1993 which will be filtered out.
    # We will handle the user's requested 'Ascending' order LOCALLY at the end.
    
    api_sort_order = arxiv.SortOrder.Descending

    # Heuristic: Fetch more papers to filter for impact
    fetch_multiplier = 3
    fetch_limit = min((max_results + offset) * fetch_multiplier, 300)
    
    search = arxiv.Search(
        query=query,
        max_results=fetch_limit, 
        sort_by=sort_by,
        sort_order=api_sort_order
    )
    
    candidates = []
    skipped = 0
    processed_count = 0
    
    try:
        generator = client.results(search)
        
        for result in generator:
            processed_count += 1
            
            # Result.published check
            if result.published > start_date:
                # Calculate Heuristic Impact Score
                impact_score = 0
                
                # 1. Conference/Journal Mentions (High intent of quality)
                meta_text = (result.comment or "") + " " + (result.journal_ref or "")
                
                # Check for top venues (case insensitive usually, but acronyms are UPCASE)
                top_venues = ["CVPR", "ICCV", "ECCV", "NEURIPS", "NIPS", "ICML", "ICLR", "AAAI", "NATURE", "SCIENCE", "SIGGRAPH", "ACL", "EMNLP"]
                
                meta_upper = meta_text.upper()
                if any(v in meta_upper for v in top_venues):
                     impact_score += 10
                     
                # 2. Code Availability
                if "github.com" in result.summary.lower():
                    impact_score += 5
                    
                # 3. "State of the Art" / "SOTA" claims
                if "state-of-the-art" in result.summary.lower() or "sota" in result.summary.lower():
                    impact_score += 3
                
                # 4. Recency Boost
                days_old = (today - result.published).days
                recency_score = max(0, 5 - (days_old // 30)) 
                
                final_sort_score = impact_score + recency_score
                
                paper = Paper(
                    title=result.title,
                    summary=result.summary,
                    published=result.published,
                    pdf_url=result.pdf_url,
                    entry_id=result.entry_id,
                    citation_count=final_sort_score, # Store heuristic
                    source="arxiv"
                )
                candidates.append(paper)
            else:
                 skipped += 1
                 if skipped > 100: break # Increased buffer for diverse pool
    
    except Exception as e:
        logger.error(f"Error fetching from Arxiv: {e}")
        print(f"Error fetching papers: {e}")

    # Local Sort by Heuristic Score
    candidates.sort(key=lambda x: x.citation_count, reverse=True)
    
    # Select the top candidates based on offset/limit logic
    final_results = candidates[offset : offset + max_results]
    
    # FINAL SORT: Date based
    if sort_order.lower() == "ascending":
        print("Sorting output by Date ASCENDING (Oldest First).")
        final_results.sort(key=lambda x: x.published)
    else:
        # Default: Newest First (Descending)
        final_results.sort(key=lambda x: x.published, reverse=True)
    
    # Debug print to show impact
    # count high scores
    impact_papers = [p for p in final_results if p.citation_count >= 10]
    if impact_papers:
        print(f"  -> Found {len(impact_papers)} papers with high impact signals (Conference/Journal/Code).")

    return final_results

if __name__ == "__main__":
    # Test
    print("Testing Mappings:")
    print(f"AI -> {CategoryMapper.get_code('AI')}")
    print(f"Cosmology -> {CategoryMapper.get_code('Cosmology')}")
    print(f"Quantum Computing -> {CategoryMapper.get_code('Quantum Computing')}")
    print(f"Generative Models -> {CategoryMapper.get_code('Generative Models')}") # Should be keyword
    
    print("\nFetching Test:")
    papers = fetch_arxiv_papers("Generative Models", days=30, max_results=5)
    for p in papers:
        print(f"{p.published} - {p.title}")
