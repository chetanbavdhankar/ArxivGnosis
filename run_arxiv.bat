@echo off
echo Starting ArxivGnosis...
echo Defaulting to Gemini. Use arguments to switch.
echo Example: run_arxiv.bat --provider openai --model gpt-4o

python main.py %*
pause
