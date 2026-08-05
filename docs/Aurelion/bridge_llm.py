# bridge_llm.py — tiny local LLM bridge
import os, time
from typing import Optional

try:
    import requests
except Exception:
    requests = None

class LLMBridge:
    def __init__(self, backend="none", ollama_model="mistral", gpt4all_model="ggml-model-gpt4all-falcon-q4_0.bin",
                 reply_max_chars=360):
        self.backend = backend
        self.ollama_model = ollama_model
        self.gpt4all_model = gpt4all_model
        self.reply_max_chars = reply_max_chars
        self._gpt4all_model_obj = None

    def set_backend(self, backend: str, model: Optional[str] = None):
        self.backend = backend
        if backend == "ollama" and model:
            self.ollama_model = model
        if backend == "gpt4all" and model:
            self.gpt4all_model = model
            self._gpt4all_model_obj = None  # reload lazily

    def reply(self, prompt: str) -> str:
        if self.backend == "none":
            return (f"[Aurelion] I read your message. I’m in safe bridge mode and "
                    f"will keep learning from your approved corpora. You said: {prompt}")[: self.reply_max_chars]

        if self.backend == "ollama":
            if requests is None:
                return "(ollama selected, but 'requests' is not installed)"
            try:
                r = requests.post("http://localhost:11434/api/generate",
                                  json={"model": self.ollama_model, "prompt": prompt, "stream": False},
                                  timeout=60)
                r.raise_for_status()
                data = r.json()
                out = data.get("response", "")
                return out[: self.reply_max_chars] if out else "(no response)"
            except Exception as e:
                return f"(ollama error: {e})"

        if self.backend == "gpt4all":
            try:
                from gpt4all import GPT4All
                if self._gpt4all_model_obj is None:
                    self._gpt4all_model_obj = GPT4All(self.gpt4all_model)
                with self._gpt4all_model_obj.chat_session():
                    out = self._gpt4all_model_obj.generate(prompt, max_tokens=180)
                return out[: self.reply_max_chars]
            except Exception as e:
                return f"(gpt4all error: {e})"

        return "(unknown backend)"
