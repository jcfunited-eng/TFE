# aurelion_core_v10_4_bridge.py
# Bridge shell that exposes LNO commands and an easy "safe mode" toggle.
# No external libraries required.

import json, os, sys, time
from pathlib import Path

# Import the LNO module next to this file
try:
    import aurelion_core_v10_4_lno as lno
except Exception as e:
    print("[FATAL] Could not import aurelion_core_v10_4_lno.py:", e)
    sys.exit(1)

APP = "Aurelion v10.4 Bridge — LNO Control Shell"
BASE = Path(__file__).parent.resolve()
CFG_F = BASE / "config" / "lno.yaml"

HELP = """
Bridge Commands:
  /lno state                 -> Show LNO config and counts
  /lno seed                  -> Seed a demo residue (tries to approve a law)
  /lno laws                  -> List stored proto-laws
  /lno get <LAW_ID>          -> Print a stored law
  /lno mom <LAW_ID>          -> One-line explanation for Mom
  /lno safe on               -> Relax guards (easier approvals)
  /lno safe off              -> Restore strict defaults
  /quit
"""

def write_yaml_like(path: Path, lines: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(lines)

def set_safe_mode(on: bool):
    # Create/overwrite config with relaxed or strict values
    if on:
        yaml = f"""# config/lno.yaml (SAFE MODE — relaxed OSF/steps for demo)
version: "10.4.0"
phi_cap: 0.14
depth_cap: 28
step_cap: 196
random_jitter: 0.02
osf:
  entropy_jump: 0.60
  affect_polarity: 0.8
ethics_floor:
  care: 0.20
  fairness: 0.20
  autonomy: 0.15
  prudence: 0.15
bias_window: 64
residue_decay:
  reject_fast: 3
  quarantine: 14
logging:
  level: INFO
  file: "{(BASE / 'logs' / 'lno_events.ndjson').as_posix()}"
persistence:
  base_dir: "{(BASE / 'memory' / 'morphogen').as_posix()}"
  atomic_writes: true
  versions_per_law: 10
"""
        write_yaml_like(CFG_F, yaml)
        return "[safe] ON — relaxed OSF (entropy_jump=0.60), step_cap=196, phi_cap=0.14"
    else:
        lno.ensure_default_cfg()
        return "[safe] OFF — restored strict defaults"

def cmd_lno_state():
    cfg = lno.load_cfg_yaml_like()
    lno.cmd_state(cfg)

def cmd_lno_seed():
    cfg = lno.load_cfg_yaml_like()
    lno.cmd_seed_demo(cfg)

def cmd_lno_laws():
    lno.cmd_laws_list()

def cmd_lno_get(law_id):
    lno.cmd_law_get(law_id)

def cmd_lno_mom(law_id):
    lno.cmd_mom_explain(law_id)

def main():
    # Make sure base LNO storage/config exist
    lno.ensure_default_cfg()
    lno.ensure_storage()
    print(APP)
    print(HELP.strip())
    while True:
        try:
            msg = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[exit]")
            break
        if not msg:
            continue
        parts = msg.split()
        if parts[0].lower() in ["/quit","/exit"]:
            break

        # /lno ...
        if parts[0].lower() == "/lno":
            if len(parts)==1:
                print("[INFO] commands:", HELP.strip().replace("\n","  |  "))
                continue
            sub = parts[1].lower()

            if sub == "state":
                cmd_lno_state()
            elif sub == "seed":
                cmd_lno_seed()
            elif sub == "laws":
                cmd_lno_laws()
            elif sub == "get" and len(parts)>=3:
                cmd_lno_get(parts[2])
            elif sub == "mom" and len(parts)>=3:
                cmd_lno_mom(parts[2])
            elif sub == "safe" and len(parts)>=3:
                flag = parts[2].lower()
                if flag == "on":
                    print(set_safe_mode(True))
                elif flag == "off":
                    print(set_safe_mode(False))
                else:
                    print("[ERR] use: /lno safe on | off")
            else:
                print("[INFO] commands:", HELP.strip().replace("\n","  |  "))
        else:
            print("[INFO] commands:", HELP.strip().replace("\n","  |  "))

if __name__ == "__main__":
    main()
