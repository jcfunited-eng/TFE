
# aurelion_v4_chat.py
from __future__ import annotations
import os, sys, time, threading, json, numpy as np
from morphospace import Morphospace
from morphospace_save import save_morphospace, load_morphospace, consolidate, autosave
from language_bridge import TinyVocab
from intrinsic_motivation import DriveController

BANNER = "Aurelion v4 — 8x8 Morphospace (128-dim)\nRegions: Core | Interface | Regulator | Associator\nTone: Balanced Hybrid\nCommands: /state /save /load /sleep /quit\n"

class AurelionChat:
    def __init__(self, persist=True, state_dir="v4_state"):
        self.ms = Morphospace(dim=128, grid=(8,8), seed=42)
        self.vocab = TinyVocab(dim=128, seed=2024)
        self.drive = DriveController()
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)
        self.persist = persist
        self.running = True
        self.lock = threading.Lock()
        self.th = threading.Thread(target=self._auto_loop, daemon=True)
        self.th.start()

    def _auto_loop(self):
        while self.running:
            time.sleep(2.0)
            with self.lock:
                goal = self.drive.propose_microgoal(self.ms)
                if goal == "REST":
                    metrics = self.ms.step(alpha_align=0.18, beta_goal=0.04, gamma_plastic=0.03, theta_energy_gain=0.06)
                elif goal == "EXPLORE":
                    stim = np.random.normal(0, 0.1, size=(self.ms.dim,))
                    stim = stim / (np.linalg.norm(stim)+1e-9)
                    metrics = self.ms.step(sigma_noise=0.02, stimulus=stim)
                else:
                    metrics = self.ms.step(alpha_align=0.14, beta_goal=0.08, gamma_plastic=0.06)
                score = self.drive.score(metrics["phi"], metrics["energy"], metrics["entropy"])
                if self.persist:
                    autosave(self.ms, folder=self.state_dir, every_steps=100)
                print(f"[auto] t={self.ms.step_n:04d} φ={metrics['phi']:.3f} E={metrics['energy']:.3f} H={metrics['entropy']:.3f} goal={goal} score={score:+.3f}")
                sys.stdout.flush()

    def handle(self, text: str):
        if text.startswith("/"):
            cmd = text.strip().lower()
            if cmd == "/state":
                print(f"Nodes={len(self.ms.nodes)} φ={self.ms.phi():.3f} H={self.ms.entropy():.3f} E={self.ms.energy_mean():.3f}")
            elif cmd == "/save":
                path = os.path.join(self.state_dir, f"manual_step{self.ms.step_n}.json")
                save_morphospace(self.ms, path); print(f"Saved {path}")
            elif cmd == "/load":
                latest = self._latest_state()
                if latest:
                    m = load_morphospace(latest)
                    self.ms.nodes = m.nodes; self.ms.regions = m.regions; self.ms.coupling = m.coupling
                    self.ms.history = m.history; self.ms.step_n = m.step_n
                    print(f"Loaded {latest}")
                else:
                    print("No saved state found.")
            elif cmd == "/sleep":
                changes = consolidate(self.ms)
                print(f"Consolidation made {changes} structural changes.")
            elif cmd == "/quit":
                self.running = False
                print("Goodbye."); os._exit(0)
            else:
                print("Unknown command. /state /save /load /sleep /quit")
            return

        v = self.vocab.encode(text)
        with self.lock:
            m = self.ms.step(stimulus=v, beta_goal=0.07, gamma_plastic=0.05)
        reply = self.vocab.phrase_from_state(v)
        print(f"Aurelion: {reply}  (φ={m['phi']:.3f}, E={m['energy']:.3f}, H={m['entropy']:.3f})")

    def _latest_state(self):
        if not os.path.isdir(self.state_dir): return None
        files = [os.path.join(self.state_dir, f) for f in os.listdir(self.state_dir) if f.endswith('.json')]
        return max(files, key=os.path.getmtime) if files else None

def main():
    print(BANNER)
    chat = AurelionChat(persist=True)
    while True:
        try:
            msg = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting."); break
        chat.handle(msg)

if __name__ == "__main__":
    main()
