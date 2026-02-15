from pydantic import BaseModel
from llm_factory import LLMFactory
import logging
import json

logger = logging.getLogger(__name__)

class PaperMetrics(BaseModel):
    breakthrough_potential: int
    practical_utility: int
    scientific_impact: int
    layman_accessibility: int
    novelty: int
    interdisciplinary_potential: int
    code_data_availability: int
    clarity_of_presentation: int
    social_relevance: int
    entertainment_value: int
    total_score: int
    rationale: str

def score_paper(title: str, abstract: str, llm_factory: LLMFactory) -> PaperMetrics:
    """
    Analyzes a paper abstract using the provided LLM and returns scores.
    """
    
    metrics_list = [
        "1. Breakthrough Potential (0-10): Paradigm shift likelihood.",
        "2. Practical Utility (0-10): Immediate application potential.",
        "3. Scientific Impact (0-10): Opening new research directions.",
        "4. Layman Accessibility (0-10): Understandability for non-experts.",
        "5. Novelty (0-10): Uniqueness of approach.",
        "6. Interdisciplinary Potential (0-10): Connection across fields.",
        "7. Code/Data Availability (0-10): Inference from abstract availability.",
        "8. Clarity of Presentation (0-10): Abstract quality.",
        "9. Social Relevance (0-10): Relevance to societal issues.",
        "10. Entertainment Value (0-10): How 'cool' or surprising it is."
    ]
    
    system_prompt = "You are an expert scientific reviewer. Analyze the provided research paper abstract and score it on a scale of 0-10 for the specified metrics based ONLY on the abstract."
    
    user_prompt = f"""
    Paper Title: {title}
    Abstract: {abstract}
    
    Metrics:
    {chr(10).join(metrics_list)}
    
    Provide the output strictly in valid JSON format matching the schema provided.
    Ensure "total_score" is simply the sum of all individual scores.
    Ensure "rationale" is a concise 2-sentence explanation.
    """
    
    try:
        metrics = llm_factory.generate_json(system_prompt, user_prompt, PaperMetrics)
        
        # Recalculate total_score to ensure consistency and avoid hallucinations
        # We can also apply weights here if desired. For now, simple sum is transparent.
        metrics.total_score = (
            metrics.breakthrough_potential +
            metrics.practical_utility +
            metrics.scientific_impact +
            metrics.layman_accessibility +
            metrics.novelty +
            metrics.interdisciplinary_potential +
            metrics.code_data_availability +
            metrics.clarity_of_presentation +
            metrics.social_relevance +
            metrics.entertainment_value
        )
        return metrics
    except Exception as e:
        logger.error(f"Error scoring paper '{title}': {e}")
        # Return default 0 scores on error
        return PaperMetrics(
            breakthrough_potential=0, practical_utility=0, scientific_impact=0,
            layman_accessibility=0, novelty=0, interdisciplinary_potential=0,
            code_data_availability=0, clarity_of_presentation=0, social_relevance=0,
            entertainment_value=0, total_score=0, rationale=f"Error: {e}"
        )
