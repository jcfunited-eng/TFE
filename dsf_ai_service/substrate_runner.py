"""
Substrate runner — standalone process hosting _guala on a Unix socket.
JSON-over-newline protocol. Single-threaded request dispatch.

GL-ARCH-FRONTEND-SPLIT-WC-20260614-01, Phase 1.

Usage:
    python -m dsf_ai_service.substrate_runner
"""
import asyncio
import json
import os
import signal
import sys
import threading
import time
import traceback

SOCKET_PATH = os.environ.get("SUBSTRATE_SOCKET", "/shared/substrate.sock")
HEARTBEAT_PATH = os.environ.get("SUBSTRATE_HEARTBEAT", "/shared/substrate.alive")
STATE_DIR = os.environ.get("STATE_DIR", "/mnt/efs/guala")

_guala = None
_shutdown = False

RUNTIME_CONFIG_FILE = "guala_runtime_config.json"


def _runtime_config_path():
    return os.path.join(STATE_DIR, RUNTIME_CONFIG_FILE)


def _write_runtime_config(data):
    """Write runtime config with fsync — survives SIGKILL."""
    path = _runtime_config_path()
    tmp = path + ".tmp"
    with open(tmp, 'w') as f:
        json.dump(data, f)
        f.flush()
        os.fsync(f.fileno())
    os.rename(tmp, path)


def _read_runtime_config():
    """Read runtime config if it exists. Returns dict or None."""
    path = _runtime_config_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


# ═══════════════════════════════════════════════════════════════
# Boot
# ═══════════════════════════════════════════════════════════════

def boot_substrate():
    """Boot the substrate engine — mirrors _gl_init() in app.py."""
    global _guala

    os.makedirs(STATE_DIR, exist_ok=True)

    from dsf_ai_service.v4.gualaloom_v5_engine import Guala, CorpusItem

    g = Guala()

    # Seed corpora (same as app.py)
    CORPUS = [
        "the sun rises in the morning",
        "water flows down the river",
        "birds sing in the trees",
        "the wind blows through the leaves",
        "stars shine in the night sky",
    ]
    g._corpora["legacy_seed"] = CorpusItem(
        corpus_id="legacy_seed", title="Seed Corpus", lines=CORPUS)

    g.load_full_state(STATE_DIR)

    # Identity guard
    EXPECTED_IDENTITY = "cdef9bcf"
    loaded_id = getattr(g, '_guala_identity', None) or ""
    if loaded_id and not loaded_id.startswith(EXPECTED_IDENTITY):
        print(f"[substrate] IDENTITY MISMATCH: got {loaded_id[:8]}, "
              f"expected {EXPECTED_IDENTITY}")

    # Runtime config: persisted decay_paused flag (survives restarts)
    rt_cfg = _read_runtime_config()
    if rt_cfg is not None:
        decay_paused = rt_cfg.get("decay_paused", True)
        os.environ["DECAY_PAUSED"] = "1" if decay_paused else "0"
        print(f"[substrate] Runtime config: decay_paused={decay_paused}")
    # else: fall back to DECAY_PAUSED env var (set by ECS task def)

    # Dream gate
    gate_marker = os.path.join(STATE_DIR, "dream_gate_cleared.json")
    if os.environ.get("DECAY_PAUSED", "0") != "1" and not os.path.exists(gate_marker):
        raise RuntimeError("DREAM GATE: decay may not resume before forced dream")

    # Blocklist
    CORPUS_BLOCKLIST = {"oxford-guide-to-english-grammar"}
    for cid in CORPUS_BLOCKLIST:
        if cid in g._corpora:
            del g._corpora[cid]

    # Start autonomy loop
    g.start_autonomy_loop(interval=0.05)
    s = g.introspect()
    print(f"[substrate] Booted: vocab={s['vocab']} reads={s['reads']} "
          f"tick={g.tick} atlas={s['atlas_entries']}")

    _guala = g

    # Wake from sleep if marker exists
    try:
        from dsf_ai_service.v4.gualaloom_v5_engine import check_sleep_marker
        marker = check_sleep_marker(STATE_DIR)
        if marker is not None:
            _guala.wake_from_sleep(state_dir=STATE_DIR)
            print(f"[substrate] Woke from sleep marker")
    except Exception as e:
        print(f"[substrate] Sleep marker check failed: {e}")

    print(f"[substrate] Ready on {SOCKET_PATH}")


# ═══════════════════════════════════════════════════════════════
# Op dispatch
# ═══════════════════════════════════════════════════════════════

def dispatch(op, args):
    """Dispatch a single op. Returns result dict. Raises on error."""
    if _guala is None:
        raise RuntimeError("substrate not ready")

    handler = OP_HANDLERS.get(op)
    if handler is None:
        raise ValueError(f"unknown op: {op}")
    return handler(args)


# ── v7 ops ──────────────────────────────────────────────────────

def handle_v7_state(args):
    session_id = args.get("session_id", "default")
    t0 = time.time()
    from dsf_ai_service.substrate.v7_engine import get_or_create_session
    session = get_or_create_session(session_id, engine=_guala)
    t1 = time.time()
    result = session.get_state(engine=_guala)
    t2 = time.time()
    print(f"[v7-state] sid={session_id} session={int((t1-t0)*1000)}ms "
          f"get_state={int((t2-t1)*1000)}ms total={int((t2-t0)*1000)}ms")
    return result


def handle_v7_converse(args):
    session_id = args.get("session_id", "default")
    text = args.get("text", "")
    from dsf_ai_service.substrate.v7_engine import get_or_create_session, save_session
    session = get_or_create_session(session_id, engine=_guala)
    result = session.converse(text)
    try:
        save_session(session)
    except Exception:
        pass
    result["session_id"] = session_id
    return result


def handle_v7_feedback(args):
    session_id = args.get("session_id", "default")
    correct = args.get("correct", "")
    expected_tokens = args.get("expected_tokens", [])
    from dsf_ai_service.substrate.v7_engine import get_or_create_session, save_session
    session = get_or_create_session(session_id, engine=_guala)
    result = session.apply_feedback(correct, expected_tokens)
    try:
        save_session(session)
    except Exception:
        pass
    result["session_id"] = session_id
    return result


def handle_v7_quiet(args):
    session_id = args.get("session_id", "default")
    n_ticks = min(args.get("n_ticks", 10), 50)
    from dsf_ai_service.substrate.v7_engine import get_or_create_session, save_session
    session = get_or_create_session(session_id, engine=_guala)
    results = session.quiet_tick(n_ticks)
    try:
        save_session(session)
    except Exception:
        pass
    total_replayed = sum(len(r["replayed"]) for r in results)
    total_commits = sum(len(r["commits"]) for r in results)
    return {"session_id": session_id, "ticks": len(results),
            "replayed": total_replayed, "commits": total_commits}


def handle_v7_save(args):
    session_id = args.get("session_id", "default")
    from dsf_ai_service.substrate.v7_engine import get_or_create_session, save_session
    session = get_or_create_session(session_id, engine=_guala)
    save_session(session)
    data = session.to_json()
    return {"saved": True, "session_id": session_id,
            "schema_version": data.get("schema_version"),
            "tick": data.get("tick"),
            "n_sections": len(data.get("sections", {})),
            "vocab_size": sum(len(v) for v in session.vocab.values())}


# ── gualaloom_post — the command dispatcher ──────────────────────

def handle_gualaloom_post(args):
    """Dispatch a gualaloom chat command. Mirrors gualaloom_chat() in app.py."""
    command = (args.get("command") or "").strip().lower()
    text = args.get("text", "")
    source = args.get("source", "joe")

    if _guala.is_asleep and command != "/status":
        return {
            "response": "she is sleeping...",
            "asleep": True,
            "sleep_tick": _guala.tick,
            "motifs": _guala.introspect()["vocab"],
        }

    if command == "/status":
        return _cmd_status()
    elif command == "/events":
        return _cmd_events(text)
    elif command == "/presence":
        return _cmd_presence(text)
    elif command == "/sleep":
        return _cmd_sleep()
    elif command == "/wake":
        return _cmd_wake(text)
    elif command == "/rest":
        return _cmd_rest(text)
    elif command.startswith("/picture "):
        return _cmd_picture(command)
    elif command == "/diag":
        return _cmd_diag()
    elif command.startswith("/addbook:"):
        return _cmd_addbook(command, text)
    elif command.startswith("/removebook:"):
        return _cmd_removebook(command)
    elif command.startswith("/addpicture:"):
        return _cmd_addpicture(command, text)
    elif command.startswith("/addpdf:"):
        return _cmd_addpdf(command, text)
    elif command.startswith("/addsound:"):
        return _cmd_addsound(command, text)
    elif command.startswith("/bundle:"):
        return _cmd_bundle(command, text)
    else:
        return _cmd_converse(text, source)


def _cmd_status():
    s = _guala.introspect()
    n = s["needs"]
    ph = _guala.persistence_health(STATE_DIR)
    ph["last_s3_backup"] = None
    sec_parts = []
    for nm, sec in s["sections"].items():
        sec_parts.append(f"{nm}: {sec['modes']}m/{sec['commits']}c")
    id_short = (ph.get("guala_identity") or "none")[:8]
    return {
        "response": (
            f"id: {id_short}.. | schema: {ph.get('schema_version', '?')}\n"
            f"vocab: {s['vocab']} | reads: {s['reads']} | tick: {s['tick']}\n"
            f"sections: {' | '.join(sec_parts)}\n"
            f"atlas: {s['cross_modal_bindings']} cross-modal / {s['atlas_entries']} entries\n"
            f"needs: stab={n['stability']:.3f} nov={n['novelty']:.3f} "
            f"conn={n['connection']:.3f} v={n['valence']:+.3f} a={n['arousal']:.3f}\n"
            f"pair-bond: {'on' if s['pair_bond_active'] else 'off'} | "
            f"recoveries(lifetime): {s['suffering_events']} | "
            f"coord: att={s['coordinator_attentions']} act={s['coordinator_actions']}\n"
            f"persistence: save@tick={ph['last_save_tick']} "
            f"files={'all' if not ph['files_missing'] else 'MISSING:' + ','.join(ph['files_missing'])} "
            f"boot={'ok' if ph['load_successful_at_boot'] else 'FAILED'} "
            f"integrity={'ok' if not ph.get('integrity_errors') else 'ERRORS'}\n"
            f"snapshots: {ph.get('snapshots_available', 0)} | "
            f"events: {ph.get('events_log', {}).get('current_file_size_bytes', 0)}B\n"
            f"deep: {s.get('deep_atlas', {}).get('n_entries', 0)} entries "
            f"str={s.get('deep_atlas', {}).get('total_strength', 0)} "
            f"surv={s.get('deep_atlas', {}).get('promotions_survival', 0)} "
            f"ep={s.get('deep_atlas', {}).get('promotions_episodic', 0)} "
            f"reinst={s.get('deep_atlas', {}).get('reinstatements_since_boot', 0)}"
        ),
        "motifs": s["vocab"],
        "vocab": s["vocab"],
        "asleep": _guala.is_asleep,
        "persistence_health": ph,
        "atlas_health": s.get("atlas_health", {}),
        "presence": s.get("presence", {}),
        "pair_bond": s.get("pair_bond", {}),
        "deep_atlas": s.get("deep_atlas", {}),
        "ladder": s.get("ladder", {}),
        "n_sounds": s.get("n_sounds", 0),
        "sounds": [{"item_id": snd["item_id"], "title": snd["title"],
                    "times_attended": snd.get("times_attended", 0)}
                   for snd in s.get("sounds", [])[-10:]],
        "current_activity": s.get("current_activity"),
        "activity_history_summary": s.get("activity_history_summary", {}),
        "n_motifs": s.get("n_motifs", 0),
        "n_corpora": len(s.get("corpora", [])),
        "corpora": [{"corpus_id": c["corpus_id"], "title": c["title"]}
                    for c in s.get("corpora", [])[-10:]],
        "sensory_items": len(s.get("sensory_items", [])),
        "n_visual_fragments": s.get("n_visual_fragments", 0),
        "n_visual_motifs": s.get("n_visual_motifs", 0),
        "sight_section": {"n_motifs": s.get("n_visual_motifs", 0)},
        "n_pictures": len(s.get("pictures", [])),
        "pictures": [{"item_id": p["item_id"], "title": p["title"],
                      "times_attended": p["times_attended"]}
                     for p in s.get("pictures", [])[-10:]],
        "n_videos": len(s.get("videos", [])),
    }


def _cmd_events(text):
    since_tick = 0
    try:
        since_tick = int(text.strip()) if text.strip() else 0
    except ValueError:
        pass
    events = _guala.get_recent_events(since_tick=since_tick, limit=50)
    return {"response": f"{len(events)} events",
            "motifs": _guala.introspect()["vocab"],
            "events": events}


def _cmd_presence(text):
    source = text.strip().lower() if text.strip() else "joe"
    if source in {"joe", "wc", "c1"}:
        if not _guala.coordinator._presence.get(source, False):
            _guala.coordinator.wake(source, _guala, _guala.needs, _guala.atlas)
            _guala._log_substrate_event("presence_heartbeat",
                                        source=source, action="wake")
        else:
            _guala.coordinator.update_last_input(source, _guala.tick)
    return {"response": "ok", "motifs": _guala.introspect()["vocab"]}


def _cmd_sleep():
    result = _guala.manual_sleep()
    return {"response": json.dumps(result), "motifs": _guala.introspect()["vocab"]}


def _cmd_wake(text):
    source = text.strip().lower() if text else "joe"
    if source not in {"joe", "wc", "c1"}:
        return {"response": f"wake: unknown source '{source}'", "motifs": 0}
    result = _guala.coordinator.wake(source, _guala, _guala.needs, _guala.atlas)
    _guala.log_event(STATE_DIR, "wake", source=source)
    return {"response": json.dumps(result), "motifs": _guala.introspect()["vocab"]}


def _cmd_rest(text):
    source = text.strip().lower() if text else "joe"
    result = _guala.coordinator.rest(source, _guala, reason="voluntary")
    _guala.log_event(STATE_DIR, "rest", source=source)
    return {"response": json.dumps(result), "motifs": _guala.introspect()["vocab"]}


def _cmd_picture(command):
    item_id = command.split(" ", 1)[1].strip()
    import base64 as _b64
    pic = _guala._pictures.get(item_id)
    if pic is None:
        return {"response": f"picture not found: {item_id}", "motifs": 0}
    orig_path = getattr(pic, 'original_path', None)
    if orig_path and os.path.exists(orig_path):
        from PIL import Image
        import io as _io
        try:
            img = Image.open(orig_path)
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            img.thumbnail((360, 360), Image.LANCZOS)
            buf = _io.BytesIO()
            img.save(buf, format='JPEG', quality=80)
            b64 = _b64.b64encode(buf.getvalue()).decode()
            return {"response": "ok", "picture_data": f"data:image/jpeg;base64,{b64}",
                    "title": pic.title, "item_id": item_id}
        except Exception:
            pass
    if pic.intensity_grid is not None:
        import numpy as np
        from PIL import Image
        import io as _io
        img = Image.fromarray((pic.intensity_grid * 255).astype(np.uint8), mode='L')
        buf = _io.BytesIO()
        img.save(buf, format='PNG')
        b64 = _b64.b64encode(buf.getvalue()).decode()
        return {"response": "ok", "picture_data": f"data:image/png;base64,{b64}",
                "title": pic.title, "item_id": item_id}
    return {"response": f"no image data for {item_id}", "motifs": 0}


def _cmd_diag():
    from collections import Counter
    atlas = _guala.atlas
    FTHRESH = 0.02
    motif_reach = Counter()
    for chi_key, entries in atlas.entries.items():
        for e in entries:
            if e.strength > FTHRESH:
                motif_reach[(e.section, e.motif_id)] += 1
    top_reach = motif_reach.most_common(20)
    return {
        "response": f"top reach: {top_reach[:5]}",
        "motifs": _guala.introspect()["vocab"],
        "top_reach": [{"section": s, "motif_id": m, "reach": r}
                      for (s, m), r in top_reach],
        "n_live_bindings": atlas.n_live_bindings(),
        "total_strength": round(atlas.total_strength(), 2),
    }


def _cmd_addbook(command, text):
    from dsf_ai_service.v4.gualaloom_v5_engine import CorpusItem
    filename = command[len("/addbook:"):]
    title = filename.replace('.txt', '').replace('_', ' ')
    corpus_id = filename.replace('.txt', '').replace(' ', '_').lower()
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return {"response": "empty book", "motifs": _guala.introspect()["vocab"]}
    _guala._corpora[corpus_id] = CorpusItem(
        corpus_id=corpus_id, title=title, lines=lines)
    _guala._log_substrate_event("corpus_added",
                                corpus_id=corpus_id, title=title,
                                n_lines=len(lines))
    return {"response": f"added \"{title}\" ({len(lines)} lines) to her library",
            "motifs": _guala.introspect()["vocab"]}


def _cmd_removebook(command):
    corpus_id = command[len("/removebook:"):].strip()
    if corpus_id in _guala._corpora:
        c = _guala._corpora[corpus_id]
        n_lines = len(c.lines)
        del _guala._corpora[corpus_id]
        _guala._log_substrate_event("corpus_removed",
                                    corpus_id=corpus_id, title=c.title,
                                    n_lines=n_lines)
        return {"response": f"removed \"{c.title}\" ({n_lines} lines)",
                "motifs": _guala.introspect()["vocab"]}
    available = [c.corpus_id for c in _guala._corpora.values()]
    return {"response": f"corpus '{corpus_id}' not found. available: {available}",
            "motifs": _guala.introspect()["vocab"]}


def _cmd_addpicture(command, text):
    import base64, hashlib
    import numpy as np
    filename = command[len("/addpicture:"):]
    title = filename.rsplit('.', 1)[0] if '.' in filename else filename
    b64_data = text.strip()
    if not b64_data:
        return {"response": "no image data", "motifs": _guala.introspect()["vocab"]}
    t0 = time.time()
    try:
        img_bytes = base64.b64decode(b64_data)
        from dsf_ai_service.app import decode_image_bytes
        from dsf_ai_service.v4.gualaloom_v5_engine import PictureItem
        _, grid, orig_w, orig_h = decode_image_bytes(img_bytes)
        item_id = hashlib.md5(img_bytes).hexdigest()[:12]
        pic_dir = os.path.join(STATE_DIR, "pictures")
        os.makedirs(pic_dir, exist_ok=True)
        ext = filename.rsplit('.', 1)[1] if '.' in filename else 'jpg'
        orig_path = os.path.join(pic_dir, f"{item_id}_original.{ext}")
        with open(orig_path, 'wb') as f:
            f.write(img_bytes)
        pic = PictureItem(item_id=item_id, title=title,
                          intensity_grid=grid, source="upload",
                          shown_at_tick=_guala.tick)
        pic.original_path = orig_path
        pic.original_width = orig_w
        pic.original_height = orig_h
        _guala._pictures[item_id] = pic
        _guala._log_substrate_event("picture_uploaded",
                                    item_id=item_id, title=title,
                                    original_size=f"{orig_w}x{orig_h}")
        result = {"response": f"showed her \"{title}\" ({orig_w}x{orig_h})",
                  "motifs": _guala.introspect()["vocab"]}
    except Exception as e:
        result = {"response": f"image decode error: {e}",
                  "motifs": _guala.introspect()["vocab"]}
    print(f"[decode-picture] {time.time()-t0:.2f}s")
    return result


def _cmd_addpdf(command, text):
    import base64
    import numpy as np
    filename = command[len("/addpdf:"):]
    title = filename.replace('.pdf', '').replace('_', ' ')
    corpus_id = filename.replace('.pdf', '').replace(' ', '_').lower()
    b64_data = text.strip()
    if not b64_data:
        return {"response": "no PDF data", "motifs": _guala.introspect()["vocab"]}
    t0 = time.time()
    try:
        from dsf_ai_service.v4.gualaloom_v5_engine import CorpusItem, PictureItem
        pdf_bytes = base64.b64decode(b64_data)
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        n_pages = len(doc)
        all_text = []
        for page in doc:
            t = page.get_text()
            if t.strip():
                all_text.append(t.strip())
        feedback = []
        if all_text:
            full_text = "\n".join(all_text)
            lines = [l.strip() for l in full_text.split('\n') if l.strip()]
            split_lines = []
            for line in lines:
                if len(line) > 200:
                    for sent in line.replace('. ', '.\n').split('\n'):
                        if sent.strip():
                            split_lines.append(sent.strip())
                else:
                    split_lines.append(line)
            _guala._corpora[corpus_id] = CorpusItem(
                corpus_id=corpus_id, title=title, lines=split_lines)
            _guala._log_substrate_event("corpus_added",
                                        corpus_id=corpus_id, title=title,
                                        n_lines=len(split_lines), source="pdf")
            feedback.append(f"text: {n_pages} pages, {len(split_lines)} lines")
        doc.close()
        if not feedback:
            feedback.append("empty PDF")
        result = {"response": f"\"{title}\": {'; '.join(feedback)}",
                  "motifs": _guala.introspect()["vocab"]}
    except Exception as e:
        result = {"response": f"PDF decode error: {e}",
                  "motifs": _guala.introspect()["vocab"]}
    print(f"[decode-pdf] {time.time()-t0:.2f}s")
    return result


def _cmd_addsound(command, text):
    import base64, hashlib, tempfile, subprocess, struct, wave
    import numpy as np
    filename = command[len("/addsound:"):]
    title = filename.rsplit('.', 1)[0] if '.' in filename else filename
    b64_data = text.strip()
    if not b64_data:
        return {"response": "no audio data", "motifs": _guala.introspect()["vocab"]}
    t0 = time.time()
    try:
        snd_bytes = base64.b64decode(b64_data)
        snd_id = hashlib.md5(snd_bytes).hexdigest()[:12]
        tmp_in = tempfile.NamedTemporaryFile(suffix='.audio', delete=False)
        tmp_in.write(snd_bytes)
        tmp_in.close()
        tmp_wav = tmp_in.name + '.wav'
        try:
            subprocess.run(["ffmpeg", "-i", tmp_in.name, "-ar", "200",
                            "-ac", "1", "-f", "wav", tmp_wav, "-y",
                            "-loglevel", "error"], check=True, timeout=30)
            with wave.open(tmp_wav, 'rb') as wf:
                sr = wf.getframerate()
                n_frames = wf.getnframes()
                raw = wf.readframes(n_frames)
            samples = np.array(struct.unpack(f'<{n_frames}h', raw),
                               dtype=np.float64) / 32768.0
            from dsf_ai_service.substrate.senses.GL_MDL_AUDITORY_CORTEX_WC_20260608_01 import (
                cochlear_transduce,)
            cochlear = cochlear_transduce(samples, sample_rate=sr)
            n_events = sum(c["n_events"] for c in cochlear.values())
            dur = len(samples) / max(sr, 1)
            from dsf_ai_service.app import deterministic_motif_id
            for bn, c in cochlear.items():
                chi = c["winding"] % 100
                _guala.atlas.record(f"audio_{bn}",
                    deterministic_motif_id(snd_id),
                    chi, _guala.tick, salience=1.5, dwell_ticks=8)
            _guala._sounds[snd_id] = {
                "item_id": snd_id, "title": title,
                "cochlear": {bn: {"winding": c["winding"],
                                  "n_events": c["n_events"]}
                             for bn, c in cochlear.items()},
                "times_attended": 0, "last_attended_tick": 0,
            }
            result = {"response": f"played her \"{title}\" ({dur:.1f}s, {n_events} events)",
                      "motifs": _guala.introspect()["vocab"]}
        except Exception as e:
            result = {"response": f"sound decode error: {e}",
                      "motifs": _guala.introspect()["vocab"]}
        finally:
            for p in [tmp_in.name, tmp_wav]:
                if os.path.exists(p):
                    os.unlink(p)
    except Exception as e:
        result = {"response": f"sound error: {e}",
                  "motifs": _guala.introspect()["vocab"]}
    print(f"[decode-sound] {time.time()-t0:.2f}s")
    return result


def _cmd_bundle(command, text):
    """Simplified bundle handler — caption + converse only for Phase 1."""
    bundle_name = command[len("/bundle:"):]
    try:
        bundle_data = json.loads(text) if text else {}
    except json.JSONDecodeError:
        bundle_data = {"caption": text}
    caption = bundle_data.get("caption", "")
    results = []
    if caption:
        try:
            _guala.read_sentence(caption, source="joe")
            results.append(f"told her \"{caption}\"")
        except Exception as e:
            results.append(f"word ERROR: {e}")
    _guala._log_substrate_event("experience_bundle",
                                name=bundle_name, lanes=results,
                                n_chis=0)
    return {
        "response": f"experience \"{bundle_name}\": {'; '.join(results)}",
        "motifs": _guala.introspect()["vocab"],
        "bundle": {"name": bundle_name, "lanes": results, "n_chis": 0},
    }


def _cmd_converse(text, source):
    text = text.strip()
    if not text:
        return {"response": "...", "motifs": _guala.introspect()["vocab"]}
    if source not in {"joe", "wc", "c1"}:
        source = "joe"
    response = _guala.converse(text, source=source)
    _guala.log_event(STATE_DIR, "source_interaction",
                     source=source, words_in=len(text.split()),
                     source_count=_guala.source_history.get(source, 0))
    recalled_pics = getattr(_guala, '_last_recalled_pictures', [])
    picture_refs = []
    seen_ids = set()
    for motif, item_id in recalled_pics:
        if item_id in seen_ids:
            continue
        pic = _guala._pictures.get(item_id)
        if pic is None:
            continue
        seen_ids.add(item_id)
        picture_refs.append({"item_id": item_id, "title": pic.title})
        if len(picture_refs) >= 4:
            break
    result = {"response": response or "...", "motifs": _guala.introspect()["vocab"]}
    if picture_refs:
        result["pictures"] = picture_refs
    return result


# ── Admin ops ──────────────────────────────────────────────────

def handle_amnesty(args):
    tick = _guala.tick
    total_before = round(_guala.atlas.total_strength(), 4)
    count = _guala.atlas.amnesty(tick)
    total_after = round(_guala.atlas.total_strength(), 4)
    _guala._log_substrate_event("amnesty_complete", entries_restamped=count,
                                 tick=tick, strength_before=total_before,
                                 strength_after=total_after)
    print(f"[UNPAUSE] Amnesty: {count} entries re-stamped to tick {tick}")
    return {"amnesty": "complete", "entries_restamped": count, "tick": tick,
            "total_strength_before": total_before,
            "total_strength_after": total_after}


def handle_force_dream(args):
    _guala._force_next_activity = ("SLEEPING", None)
    if _guala._current_activity:
        _guala._end_activity()
    _guala._log_substrate_event("force_dream_initiated", tick=_guala.tick)
    print(f"[UNPAUSE] Force dream initiated at tick {_guala.tick}")
    start_tick = _guala.tick
    for _ in range(120):
        time.sleep(0.5)
        activity = _guala._current_activity
        if activity and activity.kind == "DREAMING":
            continue
        if activity is None or activity.kind != "SLEEPING":
            events = _guala.get_recent_events(since_tick=start_tick, limit=50)
            dream_events = [e for e in events if e.get("kind") in
                           ("dream_began", "dream_artifact", "dream_promotion",
                            "deep_atlas_promotion")]
            return {"force_dream": "complete", "tick": _guala.tick,
                    "dream_events": dream_events[-10:],
                    "n_events": len(dream_events)}
    return {"force_dream": "timeout", "tick": _guala.tick,
            "current_activity": _guala._current_activity.kind if _guala._current_activity else None}


def handle_repause(args):
    os.environ["DECAY_PAUSED"] = "1"
    _write_runtime_config({"decay_paused": True})
    if _guala:
        _guala._log_substrate_event("decay_repaused", tick=_guala.tick,
                                     reason="manual_kill_switch")
    print(f"[UNPAUSE] KILL SWITCH: decay re-paused (persisted)")
    return {"repause": "active", "DECAY_PAUSED": "1", "persisted": True}


def handle_unpause(args):
    os.environ["DECAY_PAUSED"] = "0"
    _write_runtime_config({"decay_paused": False})
    tick = _guala.tick if _guala else 0
    if _guala:
        _guala._log_substrate_event("decay_unpaused", tick=tick,
                                     reason="admin_unpause")
    print(f"[UNPAUSE] Decay unpaused at tick {tick} (persisted)")
    return {"unpaused": True, "tick": tick, "persisted": True}


def handle_wake(args):
    """Force wake from sleep state."""
    if _guala and _guala.is_asleep:
        _guala.wake_from_sleep(state_dir=STATE_DIR)
        print(f"[substrate] Woke from sleep at tick {_guala.tick}")
        return {"woke": True, "tick": _guala.tick}
    return {"woke": False, "already_awake": True, "tick": _guala.tick if _guala else 0}


def handle_atlas_snapshot(args):
    dist = _guala.atlas.strength_distribution()
    return {
        "tick": _guala.tick,
        "total_strength": round(_guala.atlas.total_strength(), 2),
        "n_live_bindings": _guala.atlas.n_live_bindings(),
        "n_total_entries": sum(len(v) for v in _guala.atlas.entries.values()),
        "strength_distribution": dist,
        "decay_paused": os.environ.get("DECAY_PAUSED", "0"),
    }


def handle_backup(args):
    t0 = time.time()
    _guala.save_full_state(STATE_DIR)
    n_entries = sum(len(v) for v in _guala.atlas.entries.values())
    dt = time.time() - t0
    print(f"[backup] saved in {dt:.2f}s, {n_entries} atlas entries")
    return {"backup": "complete", "save_time_s": round(dt, 2),
            "atlas_entries": n_entries, "tick": _guala.tick}


def handle_sleep_for_deploy(args):
    if _guala.is_asleep:
        return {"ok": True, "already_asleep": True, "sleep_tick": _guala.tick}
    _guala.manual_sleep(state_dir=STATE_DIR)
    return {"ok": True, "sleep_tick": _guala.tick, "vocab": len(_guala.vocab)}


def handle_status_simple(args):
    """Simple status for /ready-equivalent queries."""
    return {
        "ready": True,
        "vocab": len(_guala.vocab),
        "tick": _guala.tick,
        "asleep": _guala.is_asleep,
    }


# ── Op registry ──────────────────────────────────────────────────

OP_HANDLERS = {
    "v7_state": handle_v7_state,
    "v7_converse": handle_v7_converse,
    "v7_feedback": handle_v7_feedback,
    "v7_quiet": handle_v7_quiet,
    "v7_save": handle_v7_save,
    "gualaloom_post": handle_gualaloom_post,
    "amnesty": handle_amnesty,
    "force_dream": handle_force_dream,
    "repause": handle_repause,
    "unpause": handle_unpause,
    "wake": handle_wake,
    "atlas_snapshot": handle_atlas_snapshot,
    "backup": handle_backup,
    "sleep_for_deploy": handle_sleep_for_deploy,
    "status": handle_status_simple,
}


# ═══════════════════════════════════════════════════════════════
# Socket server
# ═══════════════════════════════════════════════════════════════

async def handle_client(reader, writer):
    """Handle one client connection — read JSON lines, dispatch, respond."""
    peer = "client"
    try:
        while not _shutdown:
            line = await reader.readline()
            if not line:
                break
            try:
                req = json.loads(line)
            except json.JSONDecodeError as e:
                resp = {"id": "?", "ok": False, "error": f"bad json: {e}"}
                writer.write(json.dumps(resp, default=str).encode() + b"\n")
                await writer.drain()
                continue

            req_id = req.get("id", "?")
            op = req.get("op", "")
            args = req.get("args", {})

            try:
                # Run dispatch in executor to keep socket server responsive
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, dispatch, op, args)
                resp = {"id": req_id, "ok": True, "result": result}
            except Exception as e:
                resp = {"id": req_id, "ok": False,
                        "error": f"{type(e).__name__}: {e}"}
                traceback.print_exc()

            writer.write(json.dumps(resp, default=str).encode() + b"\n")
            await writer.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


def heartbeat_loop():
    """Write heartbeat file every 5s in a background thread."""
    while not _shutdown:
        try:
            hb_dir = os.path.dirname(HEARTBEAT_PATH)
            if hb_dir:
                os.makedirs(hb_dir, exist_ok=True)
            with open(HEARTBEAT_PATH, 'w') as f:
                f.write(json.dumps({
                    "alive": True,
                    "tick": _guala.tick if _guala else 0,
                    "vocab": len(_guala.vocab) if _guala else 0,
                    "ts": time.time(),
                }))
        except Exception:
            pass
        time.sleep(5)


async def run_server():
    global _shutdown

    # Clean up stale socket
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)
    sock_dir = os.path.dirname(SOCKET_PATH)
    if sock_dir:
        os.makedirs(sock_dir, exist_ok=True)

    # Boot substrate
    print(f"[substrate] Booting...")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, boot_substrate)

    # Start heartbeat
    hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    hb_thread.start()

    # Start socket server (64 MB buffer — base64 uploads can be ~13 MB)
    server = await asyncio.start_unix_server(
        handle_client, path=SOCKET_PATH, limit=64 * 1024 * 1024)
    print(f"[substrate] Listening on {SOCKET_PATH}")

    # Periodic save + compact (was in app.py startup, belongs in substrate)
    async def _periodic_save():
        save_count = 0
        while not _shutdown:
            await asyncio.sleep(60)
            if _guala is None or _shutdown:
                continue
            try:
                def _do_save():
                    t0 = time.time()
                    pre_size = _guala.events_log_size(STATE_DIR)
                    _guala.save_full_state(STATE_DIR)
                    _guala.compact_events(STATE_DIR, keep_after_offset=pre_size)
                    dt = time.time() - t0
                    print(f"[save] {dt:.2f}s")
                await loop.run_in_executor(None, _do_save)
                save_count += 1
                if save_count % 10 == 0:
                    def _snap():
                        return _guala.snapshot_state(STATE_DIR, reason="periodic")
                    snap_dir = await loop.run_in_executor(None, _snap)
                    print(f"[substrate] Snapshot: {snap_dir}")
            except Exception as e:
                print(f"[save] error: {e}")
    asyncio.ensure_future(_periodic_save())

    # Handle SIGTERM/SIGINT
    def _signal_handler():
        global _shutdown
        _shutdown = True
        print(f"[substrate] Shutting down...")
        if _guala:
            try:
                _guala.save_full_state(STATE_DIR)
                print(f"[substrate] Final save complete")
            except Exception as e:
                print(f"[substrate] Final save failed: {e}")
        server.close()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _signal_handler)

    async with server:
        await server.serve_forever()


def main():
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
