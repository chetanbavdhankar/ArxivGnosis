from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Paper:
    title: str
    summary: str
    published: datetime
    pdf_url: Optional[str]
    entry_id: str
    citation_count: int = 0  # Useful for ranking
    source: str = "arxiv"
