
import os, time, datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
from rre_semantic import SemanticStream, Resonator
from rre_semantic import tokenize, tokens_to_matrix
from mosaic_cluster import Clusterer

LOG_DIR = "mosaic_logs"
os.makedirs(LOG_DIR, exist_ok=True)

class MosaicApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Aurelion — Mosaic Scientific Console (v3.0)")
        self.dim = 128; self.window = 16; self.stride = 4; self.steps = 400
        top = ttk.Frame(root); top.pack(fill="x", padx=6, pady=6)
        ttk.Label(top, text="Corpus:").pack(side="left")
        self.corpus_path_var = tk.StringVar()
        self.corpus_entry = ttk.Entry(top, textvariable=self.corpus_path_var, width=60)
        self.corpus_entry.pack(side="left", padx=6)
        ttk.Button(top, text="Browse…", command=self.browse).pack(side="left", padx=2)
        ttk.Button(top, text="Run", command=self.run).pack(side="left", padx=8)
        mid = ttk.Frame(root); mid.pack(fill="both", expand=True, padx=6, pady=4)
        self.metrics = tk.Text(mid, width=60, height=16); self.metrics.pack(side="left", fill="both", expand=True)
        right = ttk.Frame(mid); right.pack(side="left", fill="both", expand=True)
        ttk.Label(right, text="Top Mosaic Clusters").pack(anchor="w")
        self.tree = ttk.Treeview(right, columns=("score","phi","H","energy","tokens"), show="headings", height=12)
        for col in ("score","phi","H","energy","tokens"):
            self.tree.heading(col, text=col); self.tree.column(col, width=110 if col!="tokens" else 260, anchor="w")
        self.tree.pack(fill="both", expand=True, pady=4)
        ttk.Label(right, text="Run Log").pack(anchor="w")
        self.runlog = tk.Text(right, height=8); self.runlog.pack(fill="both", expand=True)
        self.append_log("Ready. Load or browse to a corpus, then click Run.")
    def browse(self):
        p = filedialog.askopenfilename(title="Select text corpus", filetypes=[("Text", "*.txt"), ("All files", "*.*")])
        if p: self.corpus_path_var.set(p)
    def append_log(self, line):
        ts = time.strftime("[%H:%M:%S] "); self.runlog.insert("end", ts + line + "\n"); self.runlog.see("end")
    def run(self):
        path = self.corpus_path_var.get()
        if not path or not os.path.exists(path):
            messagebox.showerror("Corpus missing", "Please choose a valid text file."); return
        stream = SemanticStream.from_file(path, dim=self.dim, window=self.window, stride=self.stride)
        R = Resonator(dim=self.dim, window=self.window)
        C = Clusterer(dim=self.dim, sim_threshold=0.86)
        self.metrics.delete("1.0","end"); self.tree.delete(*self.tree.get_children())
        tokens_for_window = self.window
        for step in range(self.steps):
            W = stream.step(); phi, H = R.observe(W)
            idx = stream.idx - stream.stride
            toks = stream.tokens[max(0, idx - tokens_for_window): idx]
            C.add_window(W, phi, H, toks)
            if step % 10 == 0:
                self.metrics.delete("1.0","end")
                self.metrics.insert("end", f"Step: {step}/{self.steps}\n")
                self.metrics.insert("end", f"Recent φ mean: {np.mean(R.hist_phi[-20:]) if R.hist_phi else 0:.3f}\n")
                self.metrics.insert("end", f"Recent H mean: {np.mean(R.hist_H[-20:]) if R.hist_H else 0:.3f}\n")
                self.metrics.insert("end", f"Clusters: {len(C.clusters)}\n")
                self.tree.delete(*self.tree.get_children())
                for s in C.top_clusters(12):
                    self.tree.insert("", "end", values=(
                        f"{s['score']:.3f}", f"{s['phi']:.3f}", f"{s['H']:.3f}", f"{s['energy']:.2f}", ", ".join(s['tokens'])
                    ))
                self.root.update_idletasks(); self.root.update()
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_json = os.path.join(LOG_DIR, f"mosaic_{stamp}.json"); C.save_json(out_json); self.append_log(f"Mosaic saved: {out_json}")
        out_txt = os.path.join(LOG_DIR, f"mosaic_{stamp}_report.txt")
        with open(out_txt, "w", encoding="utf-8") as f:
            f.write("Aurelion — Mosaic Run Report (v3.0)\n")
            f.write(f"Corpus: {os.path.basename(path)}\n")
            f.write(f"Steps: {self.steps}, Window: {self.window}, Stride: {self.stride}\n\n")
            for s in C.top_clusters(12):
                line = f"[cluster {s['id']}] score={s['score']:.3f} φ={s['phi']:.3f} H={s['H']:.3f} energy={s['energy']:.2f} :: tokens={', '.join(s['tokens'])}\n"
                f.write(line)
        self.append_log(f"Report saved: {out_txt}"); self.append_log("Done.")

if __name__ == "__main__":
    root = tk.Tk(); app = MosaicApp(root); root.mainloop()
