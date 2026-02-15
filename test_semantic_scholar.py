from semanticscholar import SemanticScholar
import datetime

sch = SemanticScholar()

today = datetime.date.today()
year = today.year
last_year = year - 1

query = "cs.AI" # Or "Artificial Intelligence"
try:
    results = sch.search_paper(
        query, 
        year=f"{last_year}-{year}", 
        fields=['title', 'abstract', 'citationCount', 'venue', 'publicationDate', 'url'],
        limit=50
    )
    
    print(f"Found {len(results)} papers via standard search.")
    
    # Sort by citation count descending locally
    sorted_results = sorted(results, key=lambda x: x.citationCount if x.citationCount else 0, reverse=True)
    
    print("\nTop 5 Most Cited Papers (Last Year):")
    for paper in sorted_results[:5]:
        print(f"[{paper.citationCount} cites] {paper.title} ({paper.publicationDate})")

except Exception as e:
    print(f"Error: {e}")
