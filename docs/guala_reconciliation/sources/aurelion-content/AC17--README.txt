Aurelion — LLM + Safe Learning Ingestion Bridge (Starter Kit)
=================================================================

What this is
------------
A minimal, practical bridge that lets Aurelion:
1) Talk through a local LLM (optional; supports Ollama or GPT4All).
2) Learn safely from curated sources you approve:
   - Local files (TXT/CSV) under folders you choose.
   - Optional URLs you explicitly whitelist (no roaming).

Safety by design
----------------
- Whitelist-only: only paths/URLs matching patterns in config.json are allowed.
- File-type allow‑list: .txt, .csv by default (editable).
- Size limits (bytes, total tokens per session).
- PII scrubbing (simple: emails/phones) before storage.
- Rate limits per run and per minute for URL fetches.
- Robots.txt check (best-effort) when fetching HTTP(S).

Requirements
------------
Python 3.10+
pip install requests

Optional (for local LLMs)
- Ollama running locally (e.g., `ollama run mistral`)
- OR GPT4All Python: `pip install gpt4all` and a local model file.

Quick start
-----------
1) Edit config.json — set your SAFE paths/URLs (whitelists).
2) Put a few .txt or .csv files under a folder you approve (e.g., corpora/).
3) Run one supervised ingestion pass (local files only):
   python bridge_cli.py --ingest "corpora" --save out_store
4) Chat via your chosen backend:
   python bridge_cli.py --chat --llm none
   (later) python bridge_cli.py --chat --llm ollama --model mistral

Examples
--------
# Ingest a single file (local)
python bridge_cli.py --ingest "corpora/science_nasa.txt" --save out_store

# Ingest a whitelisted URL (set it in config.json first)
python bridge_cli.py --ingest-url "https://example.com/news.txt" --save out_store

# Chat
python bridge_cli.py --chat --llm none
python bridge_cli.py --chat --llm ollama --model mistral

Notes
-----
- This kit is purposely small and readable. It’s the *bridge* you asked for.
- We can later plug its outputs into Morphospace/RRE or other modules.
