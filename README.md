# ArxivGnosis 🏛️✨

**ArxivGnosis** is an intelligent research assistant that discovers, ranks, and summarizes Arxiv papers using your favorite LLM.

## Key Features

*   **Smart Search**: Use natural language terms (e.g., "AI", "Black Holes", "Quantum") or keywords ("Generative Models") instead of just codes.
*   **LLM Agnostic**: Supports **Ollama** (Default), **Google Gemini**, **OpenAI**, and **Anthropic** via `litellm`.
*   **Intelligent Ranking & Iteration**: Scores papers and automatically suggests fetching more if scores are low (`--min_score`).
*   **Impact Filtering**: Arxiv fetcher now prioritizes papers with **Code** (Github), **Top Conferences** (NeurIPS, CVPR), and **Recency**.
*   **Automated Content Workflow**: Generates detailed **Research Summaries** (Hooks, Analogies, Impact) for content creators.
*   **Multi-Select**: Process multiple papers at once (e.g., "1-3", "1, 5").

## Prerequisites

*   Python 3.10+
*   **For Local Use**: [Ollama](https://ollama.com) installed and running.
    *   Pull the default model: `ollama pull qwen2.5:7b`
*   **For Cloud Use**: An API Key from Google, OpenAI, or Anthropic.

## Installation

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Setup (For Cloud LLMs)**:
    If you plan to use cloud providers (Gemini, OpenAI, Anthropic), you need to set up your API keys.
    
    1.  Create a new file named `.env` in the project root folder (where `main.py` is).
    2.  Open the file with a text editor (Notepad, VS Code, etc.).
    3.  Paste your API keys in the following format:
        ```env
        # Google Gemini (Get key at aistudio.google.com)
        GEMINI_API_KEY=your_actual_key_here
        
        # OpenAI (platform.openai.com)
        OPENAI_API_KEY=sk-proj-...
        
        # Anthropic (console.anthropic.com)
        ANTHROPIC_API_KEY=sk-ant-...
        ```
    4.  Save the file.

3.  **Verify Setup**:
    *   **Local**: Run `ollama serve` in a separate terminal.
    *   **Cloud**: Ensure your `.env` file is saved.

## Usage

### Basic Usage (Local Ollama)
The system defaults to `ollama` and `qwen2.5:7b`.

```bash
# Search by Category Code
python main.py --category cs.AI
```

### Cloud LLM Usage
Once your `.env` is set up, use the `--provider` arg:

```bash
# Google Gemini (Recommended for speed/cost)
python main.py --provider gemini --model gemini/gemini-2.0-flash --category "Black Holes" --days 30

# OpenAI GPT-4o
python main.py --provider openai --model gpt-4o --category "Robot Learning"

# Anthropic Claude 3.5 Sonnet
python main.py --provider anthropic --model claude-3-5-sonnet-20240620 --category "Interpretability"
```

# Search by Natural Language Term (Auto-mapped)
python main.py --category "AI"                  # Maps to cs.AI
python main.py --category "Cosmology"           # Maps to astro-ph.CO
python main.py --category "Quantum Computing"   # Maps to quant-ph

# Search by Keyword
python main.py --category "Generative Models"   # Searches all:Generative Models
```

### Advanced Usage

**Finding the Best Papers (Iterative Search):**
```bash
# Keep fetching batches of 5 papers until one scores > 85.
# If scores are low, you can also press 'i' at the prompt to manually fetch the next batch!
python main.py --category "Generative Models" --limit 5 --min_score 85
```

```bash
python main.py --provider gemini --model gemini/gemini-1.5-pro-latest --category "Black Holes"
```

## Scoring System

The **Total Score (0-100)** is the sum of 10 key metrics evaluated by the AI:
1.  **Breakthrough Potential**
2.  **Practical Utility**
3.  **Novelty**
4.  **Scientific Impact**
5.  **Layman Accessibility** (Clarity)
6.  **Code/Data Availability**
7.  **Interdisciplinary Potential**
8.  **Clarity of Presentation**
9.  **Social Relevance**
10. **Entertainment Value**

*Note: The displayed output highlights the most critical metrics, but the Total Score reflects the overall holistic quality.*

## Arguments

*   `--category`: Arxiv category code OR natural language term OR keyword (default: `cs.AI`).
*   `--days`: Lookback period (default: 7).
*   `--limit`: Max papers per batch (default: 10).
*   `--provider`: LLM provider (default: `ollama`).
*   `--model`: Model name (default: `ollama/qwen2.5:7b`).
*   `--source`: Source for papers (default: `arxiv`). Use `semanticscholar` for "Best of Year" (impact-based) searches.
    *   *Note: For long periods (>60 days), Arxiv defaults to recent papers. Use `semanticscholar` to find the most impactful papers.*
*   `--min_score`: Minimum score threshold to stop fetching. If best paper < min_score, you can iterate to next batch.
*   `--order`: Sort order for Arxiv (default: `ascending`). Use `descending` to see newest papers first.

## Workflow for Content Creators

1.  Run the agent to find and summarize a paper (or multiple papers).
2.  Open the generated folder (e.g., `2023-10-27/Paper_Title/`).
3.  Use the `_research_summary.txt` file which contains:
    *   **The Hook**: A one-liner to grab attention.
    *   **Core Innovation**: Simplified explanation of the "Aha!" moment.
    *   **Analogies & Visuals**: Ideas for graphics/animations.
4.  (Optional) Use this structure to film your video or write a blog post.
