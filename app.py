from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from tfe_auth import get_current_user, init_auth_session, is_admin_user, login, logout
from tfe_portfolio_api import get_portfolio_df
from uf_snapshot_cache import load_snapshot, refresh_snapshot_full


st.set_page_config(page_title="Tao Financial Engine", layout="wide")


UI_ASSET_CONFIG_PATH = Path("tfe_ui_page_assets.json")

# Single approved production override from audit.
PRODUCTION_DECISION_OVERRIDE_PATTERN = "reg=TRANSITIONAL|D=-1|P=2|Rrev=1|Bsgn=-1"


def _default_ui_assets() -> Dict[str, Dict[str, Any]]:
    return {
        "landing": {
            "hero_image_url": "https://images.unsplash.com/photo-1616046229478-9901c5536a45?auto=format&fit=crop&w=1800&q=80",
            "title": "Calm Signals. Clear Decisions.",
            "subtitle": "A research-first AI assistant for simple equity decision support.",
            "show_graph_overlay": True,
            "overlay_opacity": 0.40,
        },
        "home": {
            "hero_image_url": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1800&q=80",
            "title": "Quick Ticker Check",
            "subtitle": "Get Accumulate, Hold, or Avoid in plain language.",
            "show_graph_overlay": True,
            "overlay_opacity": 0.36,
        },
        "recommendations": {
            "hero_image_url": "https://images.unsplash.com/photo-1448375240586-882707db888b?auto=format&fit=crop&w=1800&q=80",
            "title": "Recommendations",
            "subtitle": "Simple discovery without finance jargon overload.",
            "show_graph_overlay": True,
            "overlay_opacity": 0.34,
        },
        "portfolio": {
            "hero_image_url": "https://images.unsplash.com/photo-1545239351-1141bd82e8a6?auto=format&fit=crop&w=1800&q=80",
            "title": "Portfolio Advisor",
            "subtitle": "Manual holdings with plain-language guidance.",
            "show_graph_overlay": True,
            "overlay_opacity": 0.34,
        },
    }


def _load_ui_assets() -> Dict[str, Dict[str, Any]]:
    if not UI_ASSET_CONFIG_PATH.exists():
        data = _default_ui_assets()
        UI_ASSET_CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data

    try:
        data = json.loads(UI_ASSET_CONFIG_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Invalid UI asset config.")
        return data
    except Exception:
        data = _default_ui_assets()
        UI_ASSET_CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data


def _save_ui_assets(data: Dict[str, Dict[str, Any]]) -> None:
    UI_ASSET_CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _decision_vector_value(row: Dict[str, Any], index: int) -> float:
    dv = row.get("decision_vector")
    if isinstance(dv, (list, tuple)) and len(dv) > index:
        return _to_float(dv[index], 0.0)
    return 0.0


def _pattern_key_from_row(row: Dict[str, Any]) -> str:
    regime = str(row.get("regime", "UNKNOWN"))
    d_val = int(round(_decision_vector_value(row, 0)))
    p_val = int(round(_decision_vector_value(row, 4)))
    r_rev = int(round(_decision_vector_value(row, 2)))
    b_raw = _decision_vector_value(row, 5)
    if b_raw > 0.0:
        b_sign = 1
    elif b_raw < 0.0:
        b_sign = -1
    else:
        b_sign = 0
    return f"reg={regime}|D={d_val}|P={p_val}|Rrev={r_rev}|Bsgn={b_sign}"


def _decision_text_from_row(row: Dict[str, Any] | None, context: str = "general") -> str:
    if not row:
        return "Hold"

    s_uf = _to_float(row.get("S_UF"), 0.0)
    d_val = _decision_vector_value(row, 0)

    # Canonical UF policy (approved):
    # S_UF < 0.30 => Avoid
    # else D > 0 => Accumulate
    # else D == 0 => Hold
    # else D < 0 => Avoid
    if s_uf < 0.30:
        decision = "Avoid"
    elif d_val > 0.0:
        decision = "Accumulate"
    elif d_val == 0.0:
        decision = "Hold"
    else:
        decision = "Avoid"

    # Single production override (approved from full audit).
    if decision == "Avoid" and _pattern_key_from_row(row) == PRODUCTION_DECISION_OVERRIDE_PATTERN:
        decision = "Hold"

    # Portfolio UI uses Trim label in place of Avoid.
    if context == "portfolio" and decision == "Avoid":
        return "Trim"

    return decision


def _find_ticker_row(rows: List[Dict[str, Any]], ticker: str) -> Dict[str, Any] | None:
    target = ticker.strip().upper()
    for row in rows:
        if str(row.get("ticker", "")).upper() == target:
            return row
    return None


def _render_hero(asset: Dict[str, Any]) -> None:
    image_url = str(asset.get("hero_image_url", "")).strip()
    title = str(asset.get("title", "")).strip() or "Tao Financial Engine"
    subtitle = str(asset.get("subtitle", "")).strip()
    overlay_opacity = float(asset.get("overlay_opacity", 0.35))
    show_graph = bool(asset.get("show_graph_overlay", True))

    graph_svg = ""
    if show_graph:
        graph_svg = """
        <svg class='hero-graph' viewBox='0 0 1000 220' preserveAspectRatio='none'>
          <defs>
            <linearGradient id='lineGrad' x1='0' y1='0' x2='1' y2='0'>
              <stop offset='0%' stop-color='#9ad09a' stop-opacity='0.50'/>
              <stop offset='100%' stop-color='#e3d178' stop-opacity='0.50'/>
            </linearGradient>
          </defs>
          <polyline
            fill='none'
            stroke='url(#lineGrad)'
            stroke-width='5'
            points='0,170 80,165 140,160 210,168 290,145 360,150 430,130 500,136 580,112 660,105 730,98 820,90 900,78 1000,55'
          />
        </svg>
        """

    st.markdown(
        f"""
        <div class='hero' style="background-image: linear-gradient(rgba(10,17,12,{overlay_opacity}), rgba(10,17,12,{overlay_opacity})), url('{image_url}');">
          {graph_svg}
          <div class='hero-content'>
            <div class='hero-title'>{title}</div>
            <div class='hero-subtitle'>{subtitle}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_disclaimer_short() -> None:
    st.caption("For research use only. Not financial advice. No trading execution.")


def _render_disclaimer_full() -> None:
    st.markdown("### Legal & Risk Notice")
    st.markdown("- For research use only.")
    st.markdown("- This is not financial advice.")
    st.markdown("- Use at your own risk.")
    st.markdown("- No guarantee of profit or protection from loss.")
    st.markdown("- This platform cannot be used to purchase or trade assets.")


# ------------------------------------------------------------
# Global styles (high contrast + aligned top)
# ------------------------------------------------------------

st.markdown(
    """
    <style>
      .stApp {
        background:
          radial-gradient(circle at 85% 2%, #f3f6df 0%, transparent 30%),
          radial-gradient(circle at 8% 5%, #f8f0dc 0%, transparent 26%),
          linear-gradient(180deg, #f5f8f1 0%, #ecf2e7 100%);
        color: #162117;
      }

      [data-testid="stSidebar"] { display: none; }
      [data-testid="collapsedControl"] { display: none; }
      header[data-testid="stHeader"] { display: none; }

      .block-container {
        max-width: 1240px;
        padding-top: 1.0rem;
        padding-bottom: 2.2rem;
      }

      .topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border: 1px solid #cfd8cc;
        border-radius: 12px;
        background: rgba(255,255,255,0.86);
        padding: 10px 14px;
        margin-bottom: 12px;
      }

      .brand {
        font-weight: 800;
        letter-spacing: 0.4px;
        font-size: 1.07rem;
        color: #162117;
      }

      .hero {
        position: relative;
        height: 330px;
        border-radius: 16px;
        border: 1px solid #cad7c6;
        overflow: hidden;
        box-shadow: 0 10px 26px rgba(49, 76, 51, 0.15);
        background-size: cover;
        background-position: center;
        margin-bottom: 14px;
      }

      .hero-content {
        position: absolute;
        left: 26px;
        bottom: 22px;
        max-width: 700px;
        color: #f2f6ef;
        text-shadow: 0 2px 10px rgba(0,0,0,0.45);
      }

      .hero-title {
        font-size: 2.1rem;
        font-weight: 800;
        line-height: 1.15;
        color: #f6fbf2;
      }

      .hero-subtitle {
        margin-top: 8px;
        font-size: 1rem;
        line-height: 1.35;
        opacity: 0.96;
        color: #edf5e8;
      }

      .hero-graph {
        position: absolute;
        left: 0;
        right: 0;
        bottom: 0;
        height: 45%;
      }

      .surface {
        background: rgba(255,255,255,0.88);
        border: 1px solid #d2dccd;
        border-radius: 12px;
        padding: 14px;
        box-shadow: 0 4px 12px rgba(71, 90, 63, 0.08);
      }

      .stButton > button, .stFormSubmitButton > button {
        border-radius: 10px;
        border: 1px solid #8ead8d;
        background: linear-gradient(180deg, #d8ead4 0%, #c5debf 100%);
        color: #162117;
        font-weight: 700;
      }

      .stButton > button:hover, .stFormSubmitButton > button:hover {
        border-color: #638964;
      }

      .decision {
        font-size: 1.95rem;
        font-weight: 800;
        color: #173019;
        margin: 10px 0;
      }

      .stTextInput label,
      .stNumberInput label,
      .stSelectbox label,
      .stCheckbox label,
      .stRadio label,
      p, h1, h2, h3, h4, h5, h6, li, span, div {
        color: #162117 !important;
      }

      .stTextInput input,
      .stNumberInput input,
      .stSelectbox div[data-baseweb="select"] {
        background: #ffffff !important;
        color: #121b12 !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# Auth + UI assets
# ------------------------------------------------------------

init_auth_session()
user = get_current_user()
ui_assets = _load_ui_assets()


# ------------------------------------------------------------
# Public landing (login upper-right)
# ------------------------------------------------------------

if user is None:
    st.markdown("<div class='topbar'><div class='brand'>Tao Financial Engine</div><div>Research Interface</div></div>", unsafe_allow_html=True)
    _render_hero(ui_assets["landing"])

    col_l, col_r = st.columns([2.2, 1.0])
    with col_l:
        st.markdown("<div class='surface'>", unsafe_allow_html=True)
        st.subheader("Simple Decisions. Clear Boundaries.")
        st.write("Get one plain-language decision first: Accumulate, Hold, or Avoid.")
        st.write("No trading execution. No guarantee claims. Research use only.")
        st.markdown("Need deeper charting? Use external research chart tools.")
        _render_disclaimer_short()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r:
        st.markdown("<div class='surface'>", unsafe_allow_html=True)
        st.markdown("#### Sign In")
        with st.form("top_right_login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            do_login = st.form_submit_button("Sign In")
        if do_login:
            if login(username=username, password=password):
                st.success("Signed in.")
                st.rerun()
            else:
                st.error("Sign in failed.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()


# ------------------------------------------------------------
# Authenticated shell (top nav + top-right sign out)
# ------------------------------------------------------------

left, right = st.columns([5, 2])
with left:
    st.markdown("<div class='topbar'><div class='brand'>Tao Financial Engine</div><div>Calm Signals for Research Decisions</div></div>", unsafe_allow_html=True)
with right:
    c1, c2 = st.columns([2, 1])
    with c1:
        st.write(f"Signed in: **{user.username}** ({user.role})")
    with c2:
        if st.button("Sign Out"):
            logout()
            st.rerun()

nav_pages = ["Home", "Account", "Recommendations", "Watchlist", "Portfolio Advisor", "Legal"]
if is_admin_user():
    nav_pages.append("Admin Console")

if "tfe_top_nav" not in st.session_state or st.session_state["tfe_top_nav"] not in nav_pages:
    st.session_state["tfe_top_nav"] = "Home"

st.markdown("<div class='surface'>", unsafe_allow_html=True)
nav_cols = st.columns(len(nav_pages))
for i, name in enumerate(nav_pages):
    with nav_cols[i]:
        is_active = st.session_state["tfe_top_nav"] == name
        label = f"{name}" if not is_active else f"● {name}"
        if st.button(label, key=f"nav_btn_{name}", use_container_width=True):
            st.session_state["tfe_top_nav"] = name
            st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

selected_page = st.session_state["tfe_top_nav"]


# ------------------------------------------------------------
# Pages
# ------------------------------------------------------------

if selected_page == "Home":
    _render_hero(ui_assets["home"])
    st.markdown("<div class='surface'>", unsafe_allow_html=True)
    st.subheader("Quick Ticker Check")
    ticker = st.text_input("Ticker symbol", "AAPL").strip().upper()
    rows = load_snapshot()
    row = _find_ticker_row(rows, ticker)
    decision = _decision_text_from_row(row)
    st.markdown(f"<div class='decision'>Decision: {decision}</div>", unsafe_allow_html=True)
    if row:
        st.write(f"Reason: UF structure snapshot for `{ticker}` is currently `{decision}`.")
    else:
        st.write(f"Reason: No snapshot row found for `{ticker}`. Defaulting to Hold.")
    st.markdown("Need deeper analysis and charting? Use external research tools.")
    _render_disclaimer_short()
    st.markdown("</div>", unsafe_allow_html=True)

elif selected_page == "Account":
    st.markdown("<div class='surface'>", unsafe_allow_html=True)
    st.subheader("Account")
    st.write("Plan: Not connected yet (Task 5 Fix 4)")
    st.write("Status: Active session")
    st.write("Renewal/End date: Not connected yet")
    st.write("Survey status: Not connected yet")
    st.markdown("</div>", unsafe_allow_html=True)

elif selected_page == "Recommendations":
    _render_hero(ui_assets["recommendations"])
    st.markdown("<div class='surface'>", unsafe_allow_html=True)
    st.subheader("Recommendations")

    rows = load_snapshot()
    if not rows:
        st.info("No snapshot data available.")
    else:
        df = pd.DataFrame(rows)
        # verify minimal schema
        if "price" in df.columns and "ticker" in df.columns and "asset_type" in df.columns:
            df = df.copy()
            df["price"] = pd.to_numeric(df["price"], errors="coerce")
            # Canonical production policy with approved override.
            df["decision"] = df.apply(lambda r: _decision_text_from_row(r.to_dict()), axis=1)
            df["accumulate"] = df["decision"] == "Accumulate"
            df["hold"] = df["decision"] == "Hold"

            # top accumulate-only lists (example top 5 cheap and top 10 by class)
            st.markdown("#### Top lists — Accumulate-only")
            cheap_acc = df[(df["asset_type"] == "stock") & (df["price"] < 50) & df["accumulate"]].head(5)
            st.write("*Top 5 accumulated stocks under $50*")
            st.dataframe(cheap_acc[["ticker", "price", "decision"]], use_container_width=True)

            asset = st.selectbox("Asset class for top accumulates", ["stock", "etf", "index", "crypto"])
            class_acc = df[(df["asset_type"] == asset) & df["accumulate"]].head(10)
            st.write(f"*Top 10 accumulated {asset}s*")
            st.dataframe(class_acc[["ticker", "price", "decision"]], use_container_width=True)

            # full market assessment
            st.markdown("#### Full Market Assessment")
            st.markdown("All rows are processed; scroll to explore (first 50 visible).")
            st.dataframe(
                df[["ticker", "price", "asset_type", "decision"]],
                height=600,
                use_container_width=True,
            )
        else:
            st.error("Snapshot schema missing required fields.")

    if is_admin_user():
        st.info("Admin controls are available in Admin Console.")

    _render_disclaimer_short()
    st.markdown("</div>", unsafe_allow_html=True)

elif selected_page == "Watchlist":
    st.markdown("<div class='surface'>", unsafe_allow_html=True)
    st.subheader("Watchlist")
    st.write("Behavior wiring is next pass. This section is reserved and grouped in top navigation.")
    st.markdown("</div>", unsafe_allow_html=True)

elif selected_page == "Portfolio Advisor":
    _render_hero(ui_assets["portfolio"])
    st.markdown("<div class='surface'>", unsafe_allow_html=True)
    st.subheader("Portfolio Advisor")
    st.write("Manual portfolio with Accumulate/Hold/Trim signals.")
    df_portfolio = get_portfolio_df()
    if df_portfolio is None or df_portfolio.empty:
        st.info("No manual portfolio holdings found yet.")
    else:
        snapshot_rows = load_snapshot()
        snapshot_by_ticker = {
            str(r.get("ticker", "")).upper(): r
            for r in snapshot_rows
            if isinstance(r, dict)
        }

        df_view = df_portfolio.copy()
        if "ticker" in df_view.columns:
            df_view["ticker"] = df_view["ticker"].astype(str).str.upper()
            df_view["advisor_decision"] = df_view["ticker"].apply(
                lambda t: _decision_text_from_row(snapshot_by_ticker.get(t), context="portfolio")
            )
        else:
            df_view["advisor_decision"] = "Hold"

        st.dataframe(df_view, use_container_width=True)
    _render_disclaimer_short()
    st.markdown("</div>", unsafe_allow_html=True)

elif selected_page == "Legal":
    st.markdown("<div class='surface'>", unsafe_allow_html=True)
    _render_disclaimer_full()
    st.markdown("### Launch Offer Condition")
    st.markdown("- First 1,000 members can access 3 years for $25, subject to terms.")
    st.markdown("- Members in this offer must complete a monthly survey to maintain membership.")
    st.markdown("</div>", unsafe_allow_html=True)

elif selected_page == "Admin Console":
    if not is_admin_user():
        st.error("Access denied. Admin role required.")
        st.stop()

    st.markdown("<div class='surface'>", unsafe_allow_html=True)
    st.subheader("Admin Console")

    st.markdown("### Snapshot Operations")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Re-load UF snapshot from disk"):
            st.success("Snapshot reloaded.")
            st.rerun()
    with c2:
        if st.button("Rebuild FULL UF snapshot (stocks + ETFs + index + crypto)"):
            st.info("Running rebuild...")
            refresh_snapshot_full(("stock", "etf", "index", "crypto"))
            st.success("Full UF snapshot rebuilt.")

    st.markdown("### Page Visual Manager")
    st.caption("Swap image/title/subtitle per page without code changes.")

    editable_pages = ["landing", "home", "recommendations", "portfolio"]
    target = st.selectbox("Page visual set", editable_pages)
    current = ui_assets.get(target, {})

    with st.form("page_visual_editor"):
        hero_image_url = st.text_input("Hero image URL", value=str(current.get("hero_image_url", "")))
        title = st.text_input("Hero title", value=str(current.get("title", "")))
        subtitle = st.text_input("Hero subtitle", value=str(current.get("subtitle", "")))
        show_graph_overlay = st.checkbox("Show transparent graph overlay", value=bool(current.get("show_graph_overlay", True)))
        overlay_opacity = st.slider("Overlay opacity", min_value=0.10, max_value=0.70, value=float(current.get("overlay_opacity", 0.35)), step=0.01)
        save_page_visual = st.form_submit_button("Save Page Visual")

    if save_page_visual:
        ui_assets[target] = {
            "hero_image_url": hero_image_url,
            "title": title,
            "subtitle": subtitle,
            "show_graph_overlay": show_graph_overlay,
            "overlay_opacity": overlay_opacity,
        }
        _save_ui_assets(ui_assets)
        st.success(f"Saved visual settings for: {target}")
        st.rerun()

    st.markdown("### Admin Modules")
    st.write("User access management: Pending wiring")
    st.write("Survey results review: Pending wiring")
    st.write("UF/SES research metrics: Pending wiring")
    st.write("Test-user bypass management: Pending wiring")
    st.markdown("</div>", unsafe_allow_html=True)
