import os
import requests
import datetime
import json
import logging
from fpdf import FPDF
from fetcher import fetch_arxiv_papers
from ranker import score_paper, PaperMetrics
from llm_factory import LLMFactory

# Setup Logging
logger = logging.getLogger(__name__)

# Load history
HISTORY_FILE = "history.json"
history = []
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r") as f:
        history = json.load(f)

def load_history():
    global history
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)

def save_history():
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

def check_history(paper_id):
    return paper_id in history

def download_pdf(url: str, output_path: str):
    """
    Downloads a PDF file from a given URL to the specified path.
    """
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"Downloaded PDF: {url} -> {output_path}")
    except Exception as e:
        logger.error(f"Failed to download PDF {url}: {e}")

def generate_research_summary(title: str, abstract: str, llm_factory: LLMFactory) -> str:
    """
    Generates a detailed research summary and content creation guide in English.
    """
    
    system_prompt = f"""
    You are an expert research analyst and content strategist for a science/tech channel.
    Your goal is to deconstruct complex academic papers into clear, actionable summaries that a video creator can use to build a narrative.
    Focus on clarity, accuracy, and "stickiness" of ideas.
    """
    
    user_prompt = f"""
    Analyze this research paper and provide a structured summary for a content creator.
    
    Paper Title: {title}
    Abstract: {abstract}
    
    Provide the output in the following structured format:

    # 1. The "One-Liner" Hook
    (A single, punchy sentence explaining what this is and why it's cool.)

    # 2. The Core Problem
    (What specific limitation or problem does this research solve? Why was the old way bad?)

    # 3. The Solution / Innovation
    (What is the new method/insight? Name it and explain it simply.)

    # 4. How It Works (Simplified)
    (Break down the technical mechanism into 3 simple steps or components.)

    # 5. Key Results & Impact
    (What did they achieve? SOTA results? 10x speedup? New capability?)

    # 6. Analogies & Visual Ideas
    - **Analogy**: (A real-world comparison to explain the core concept)
    - **Visual Concept**: (Idea for a graphic or animation to show the mechanism)

    # 7. Technical Keywords
    (List of 3-5 key terms the audience might need defined)

    Output full, detailed paragraphs for sections 2-5.
    """
    
    try:
        script = llm_factory.generate_text(system_prompt, user_prompt)
        return script
    except Exception as e:
        logger.error(f"Error generating summary for '{title}': {e}")
        return "Error generating summary."

def process_paper(paper_obj, llm_factory: LLMFactory):
    """
    Orchestrates the download, summary generation, and saving process for a selected paper.
    """
    
    # Check history
    paper_id = paper_obj.entry_id.split('/')[-1] # Extract ID
    if check_history(paper_id):
        logger.info(f"Paper {paper_id} already processed. Skipping.")
        print(f"Paper '{paper_obj.title}' was already processed previously.")
        return

    # Setup Directory
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    # Sanitize title for folder name
    safe_title = "".join([c for c in paper_obj.title if c.isalnum() or c in (' ', '-', '_')]).strip()[:50]
    folder_path = os.path.join(today_str, safe_title)
    
    os.makedirs(folder_path, exist_ok=True)
    
    # Download PDF
    pdf_url = paper_obj.pdf_url
    pdf_filename = f"{safe_title}.pdf"
    pdf_path = os.path.join(folder_path, pdf_filename)
    download_pdf(pdf_url, pdf_path)
    
    # Generate Research Summary
    try:
        summary_text = generate_research_summary(paper_obj.title, paper_obj.summary, llm_factory)
        summary_filename = f"{safe_title}_research_summary.txt"
        summary_path = os.path.join(folder_path, summary_filename)
        
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary_text)
            
        logger.info(f"Generated summary at {summary_path}")
        print(f"Success! Files saved in: {folder_path}")
        
        # Update History
        history.append(paper_id)
        save_history()

    except Exception as e:
        logger.error(f"Failed to process summary or save files: {e}")
