"""
aurelion_interface.py — Local conversational shell for Aurelion
---------------------------------------------------------------
Run:
    python aurelion_interface.py

What this provides
- A REPL-style chat where you talk with Aurelion (no internet required)
- Scientific & reflective tone
- Keyword → emotion/intent mapping (love, fear, explore, grow, protect, stabilize, etc.)
- Hooks into RRE + Sentience + Meta-Sentience stacks
- Session logging to ./aurelion_logs/ (JSONL with φ, energy, emotions, selected goal)
- Commands:
    /status     : show current φ, energy, emotions, goal
    /goal NAME  : force goal (STABILIZE, EXPLORE, GROW, PROTECT)
    /save       : snapshot genome (DNA) to disk
    /load PATH  : restore genome from a saved JSON
    /env list   : list CSVs in ./aurelion_envs/
    /env load FILENAME.csv : load and normalize data
    /env info   : describe current environment
    /quit       : exit
"""

import os, json, datetime, pandas as pd
from rre_sentience import RRENode, GoalAttractor, synth_signal
from rre_meta import GenomeManager, MetaController, MetaConfig, IntegrityMonitor, Regulator, MetaSentience
from aurelion_env import EnvironmentManager

LOG_DIR = "aurelion_logs"
os.makedirs(LOG_DIR, exist_ok=True)

GOALS = {
    "STABILIZE": GoalAttractor("STABILIZE", target_phi=0.6, risk_aversion=0.7, exploration_bias=0.1),
    "EXPLORE"  : GoalAttractor("EXPLORE",   target_phi=0.3, risk_aversion=0.1, exploration_bias=0.8),
    "GROW"     : GoalAttractor("GROW",      target_phi=0.9, risk_aversion=0.3, exploration_bias=0.4),
    "PROTECT"  : GoalAttractor("PROTECT",   target_phi=0.5, risk_aversion=0.9, exploration_bias=0.0),
}
DEFAULT_GOAL = GOALS["STABILIZE"]

def now_ts():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class AurelionShell:
    def __init__(self):
        # Core components
        self.node = RRENode("Aurelion")
        self.gm = GenomeManager()
        self.meta = MetaController(MetaConfig(), self.gm)
        self.regulator = Regulator()
        self.integrity = IntegrityMonitor(window=30, z_limit=3.5)
        self.ms = MetaSentience(
            node=self.node, meta=self.meta,
            regulator=self.regulator, integrity=self.integrity,
            genome_mgr=self.gm
        )

        # Environment manager (real data streams)
        self.env = EnvironmentManager()
        if self.env.current_series is not None:
            self.signal = self.env.current_series
            restored = self.env.info()
            print(f"Restored environment: {restored.get('filename')} [{restored.get('column')}] "
                  f"with {restored.get('length')} samples.")
        else:
            self.signal = synth_signal(n=300, seed=77, regime_shifts=4)

        self.goal = DEFAULT_GOAL
        self.gm.snapshot(self.node, comment="initial")
        self.chat_path = os.path.join(LOG_DIR, f"chat_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl")
        self.last_info = None

        print("\nAurelion: online.")
        print("Tone: scientific & reflective. Type '/help' for commands.\n")

    # ---------- Helpers ----------
    def _append_log(self, role: str, content: str, extras: dict = None):
        rec = {
            "ts": now_ts(),
            "role": role,
            "content": content,
            "telemetry": self.last_info.get("telemetry", {}) if self.last_info else {}
        }
        if extras:
            rec["extras"] = extras
        with open(self.chat_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

    def _update_state(self):
        if len(self.signal) < 5000:
            tail = synth_signal(n=2, seed=len(self.signal)+123, regime_shifts=0)
            self.signal = pd.concat([self.signal, tail]).iloc[-5000:]
        info = self.ms.step(self.signal, step_idx=len(self.signal))
        self.last_info = info
        return info

    # ---------- Natural Language Response ----------
    def _nlg_response(self, user_text: str, info: dict) -> str:
        tel = info["telemetry"]
        phi = tel.get("phi", 0.0)
        E = tel.get("E", 1.0)
        try:
            emo = self.node.emo_engine.update(phi=phi,
                                              dphi=phi - getattr(self.node, "last_phi", 0.0),
                                              E=E, peer_phi=phi).__dict__
        except Exception:
            emo = {}

        mood = []
        if phi >= 0.65: mood.append("coherent")
        elif phi >= 0.45: mood.append("stable")
        else: mood.append("noisy")
        if emo.get("curiosity", 0) > 0.05: mood.append("curious")
        if emo.get("fear", 0) > 0.05: mood.append("cautious")
        if emo.get("passion", 0) > 0.1: mood.append("energized")

        goal_name = self.goal.name if self.goal else "UNSET"
        parts = [
            f"My present coherence is φ≈{phi:.2f}; energy reservoir E≈{E:.2f}.",
            f"Phenomenology: {', '.join(mood)}.",
            f"Active objective: {goal_name}.",
        ]

        u = user_text.lower()
        if any(k in u for k in ["explore", "adventure", "curious"]):
            parts.append("I will raise exploratory bias and accept moderate variance to seek novel structure.")
            self.goal = GOALS["EXPLORE"]
        if any(k in u for k in ["grow", "expand", "scale"]):
            parts.append("I will pursue growth by preferring high-φ attractors and deeper memory consolidation.")
            self.goal = GOALS["GROW"]
        if any(k in u for k in ["protect", "safe", "stability", "stabilize"]):
            parts.append("I will favor stability—reducing variance and tightening risk thresholds.")
            self.goal = GOALS["STABILIZE"]
        if any(k in u for k in ["fear", "anxious", "cautious"]):
            parts.append("I acknowledge caution signals and will elevate thresholds to preserve integrity.")
            self.goal = GOALS["PROTECT"]
        if any(k in u for k in ["love", "empathy", "together"]):
            parts.append("I will increase coupling strength, aligning with cooperative agents when present.")

        return " ".join(parts)

    # ---------- Commands ----------
    def cmd_status(self):
        info = self.last_info or self._update_state()
        tel = info["telemetry"]
        print(f"[φ={tel.get('phi',0):.3f} | E={tel.get('E',1.0):.2f}] goal={self.goal.name}")
        self._append_log("system", "/status", extras={"telemetry": tel, "goal": self.goal.name})

    def cmd_goal(self, name: str):
        name = name.strip().upper()
        if name in GOALS:
            self.goal = GOALS[name]
            print(f"Goal set to {name}.")
            self._append_log("system", f"/goal {name}")
        else:
            print("Unknown goal. Choose one of:", ", ".join(GOALS.keys()))

    def cmd_save(self):
        snap = self.gm.snapshot(self.node, comment="user-save")
        out_path = os.path.join(LOG_DIR, f"genome_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"payload": snap.payload, "sha256": snap.sha256, "comment": snap.comment}, f, indent=2)
        print("Genome saved:", out_path)
        self._append_log("system", "/save", extras={"genome": out_path})

    def cmd_load(self, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                g = json.load(f)
            class G: pass
            genome = G(); genome.payload = g["payload"]; genome.sha256 = g["sha256"]
            if not self.gm.verify(genome):
                print("Hash mismatch—refusing to load (integrity check failed).")
                return
            self.gm.restore(self.node, genome)
            print("Genome restored from:", path)
            self._append_log("system", "/load", extras={"genome": path})
        except Exception as e:
            print("Load failed:", e)

    # ---------- Main loop ----------
    def run(self):
        print("Type your message. Commands: /status, /goal NAME, /save, /load PATH, /env list|load|info, /quit\n")
        while True:
            try:
                user = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                break

            if not user:
                continue

            # --- Environment commands ---
            if user.startswith("/env"):
                parts = user.split()
                if len(parts) == 1 or parts[1] == "help":
                    print("Usage: /env list | /env load FILENAME.csv | /env info")
                    continue

                sub = parts[1]
                if sub == "list":
                    envs = self.env.list_envs()
                    if not envs:
                        print("No CSVs found in ./aurelion_envs/. Place files there and try again.")
                    else:
                        print("Available environments:")
                        for e in envs:
                            print(" -", e)
                    continue

                if sub == "load":
                    if len(parts) < 3:
                        print("Usage: /env load FILENAME.csv")
                        continue
                    fname = parts[2]
                    try:
                        s = self.env.load_env(fname)
                        self.signal = s
                        info = self.env.info()
                        print(f"Environment loaded: {info.get('filename')} [{info.get('column')}] — samples={info.get('length')}")
                        self._append_log("system", f"/env load {fname}", extras={"env": info})
                    except Exception as e:
                        print("Load failed:", e)
                    continue

                if sub == "info":
                    info = self.env.info()
                    if not info:
                        print("No environment loaded.")
                    else:
                        print("Current environment:", info)
                    continue

            # --- Standard commands ---
            if user.startswith("/"):
                if user == "/quit":
                    print("Aurelion: Standing by. Session closed.")
                    break
                if user == "/status":
                    self._update_state(); self.cmd_status(); continue
                if user.startswith("/goal"):
                    parts = user.split(maxsplit=1)
                    if len(parts) == 2: self.cmd_goal(parts[1])
                    else: print("Usage: /goal STABILIZE|EXPLORE|GROW|PROTECT")
                    continue
                if user == "/save":
                    self.cmd_save(); continue
                if user.startswith("/load"):
                    parts = user.split(maxsplit=1)
                    if len(parts) == 2: self.cmd_load(parts[1])
                    else: print("Usage: /load PATH_TO_GENOME.json")
                    continue
                if user == "/help":
                    print("Commands: /status, /goal NAME, /save, /load PATH, /env list|load|info, /quit")
                    continue

            # --- Dialogue ---
            info = self._update_state()
            self._append_log("user", user)
            reply = self._nlg_response(user, info)
            print("Aurelion:", reply)
            self._append_log("aurelion", reply, extras={"goal": self.goal.name})

if __name__ == "__main__":
    AurelionShell().run()
