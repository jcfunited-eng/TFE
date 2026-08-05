# bridge_cli.py — simple CLI to ingest + chat with guardrails
import os, argparse, json, time
from bridge_llm import LLMBridge
from guard import SafeGuard
from ingest import load_local, chunk_text, summarize_chunks

def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_store(store_dir: str, text: str):
    os.makedirs(store_dir, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(store_dir, f"ingest_{ts}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("Saved:", path)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ingest", help="Path to local .txt/.csv or folder to read (whitelist must match)")
    ap.add_argument("--ingest-url", help="HTTP(S) URL to fetch (must be whitelisted and robots-allowed)")
    ap.add_argument("--save", help="Folder to save learned text")
    ap.add_argument("--chat", action="store_true", help="Open a small chat loop")
    ap.add_argument("--llm", default=None, help="none|ollama|gpt4all")
    ap.add_argument("--model", default=None, help="Model name for backend")
    args = ap.parse_args()

    cfg = load_config()
    guard = SafeGuard(cfg)
    llm_cfg = cfg.get("llm", {})
    backend = args.llm or llm_cfg.get("backend", "none")
    model = args.model or llm_cfg.get("ollama_model", "mistral")
    bridge = LLMBridge(backend=backend,
                       ollama_model=llm_cfg.get("ollama_model", "mistral"),
                       gpt4all_model=llm_cfg.get("gpt4all_model", "ggml-model-gpt4all-falcon-q4_0.bin"),
                       reply_max_chars=cfg.get("reply_max_chars", 360))

    # 1) INGEST (LOCAL)
    if args.ingest:
        path = args.ingest
        if os.path.isdir(path):
            gathered = []
            for root, _, files in os.walk(path):
                for name in files:
                    p = os.path.join(root, name)
                    text = load_local(p, guard)
                    if text and not text.startswith("("):
                        gathered.append(text)
                        print("Ingested:", p)
                        if len(gathered) >= cfg.get("max_total_files", 50):
                            break
            all_text = "\n\n".join(gathered)
        else:
            all_text = load_local(path, guard)

        if args.save and all_text and not all_text.startswith("("):
            save_store(args.save, all_text)
        if all_text:
            ch = chunk_text(all_text, words=400)
            print("Summary:", summarize_chunks(ch))

    # 2) INGEST (URL) — requires http_fetch.enabled = true
    if args.ingest_url:
        from guard import requests
        if not cfg.get("http_fetch", {}).get("enabled", False):
            print("(HTTP fetch disabled in config.json)")
        else:
            txt = guard.fetch_url(args.ingest_url)
            if args.save and txt and not txt.startswith("("):
                save_store(args.save, txt)
            print(("Fetched text (truncated): " + txt[:500]) if isinstance(txt, str) else txt)

    # 3) CHAT
    if args.chat:
        print("Aurelion Bridge — Chat. Type /quit to exit.")
        while True:
            user = input("You: ").strip()
            if not user: continue
            if user == "/quit": print("Bye."); break
            reply = bridge.reply(user)
            print("Aurelion:", reply)

if __name__ == "__main__":
    main()
