import streamlit as st

from tfe_app_integration import (
    init_tfe_app_context,
    save_portfolio,
    load_portfolio,
    list_portfolios_for_tenant_as_dicts,
)

# ============================================================
# Initialize SES-Core → TFE integration once at startup
# ============================================================

# Note: environment/region are logical tags; "dev"/"local" is fine for now.
ctx = init_tfe_app_context(environment="dev", region="local")

# ============================================================
# Streamlit Page Configuration
# ============================================================

st.set_page_config(
    page_title="Tao Financial Engine",
    layout="wide",
)

st.title("Tao Financial Engine")
st.write("This dashboard is now wired to SES-Core for portfolio encryption and custody.")

# ============================================================
# Sidebar Navigation
# ============================================================

st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Select a page",
    ["Home", "Save Demo Portfolio", "View Portfolios"],
)


# ============================================================
# Helper: fixed demo tenant/user
# ============================================================

TENANT_NAME = "Tao Tenant"
USER_NAME = "Tao Primary User"


def render_home_page() -> None:
    st.subheader("Home")
    st.write(
        """
        Use the sidebar to:
        - Save a demo portfolio (encrypted using SES-Core)
        - View stored portfolios and see decrypted data

        This is a minimal integration to prove SES-Core → TFE wiring.
        """
    )


def render_save_demo_portfolio_page() -> None:
    st.subheader("Save Demo Portfolio (SES-Core Encrypted)")

    st.write(
        """
        This page saves a single demo portfolio under a fixed tenant/user.

        Tenant: `Tao Tenant`  
        User: `Tao Primary User`  
        """
    )

    # Simple form fields for demo portfolio
    with st.form("save_demo_portfolio"):
        portfolio_id = st.text_input(
            "Portfolio ID",
            value="tao-demo-001",
            help="Logical ID for this portfolio.",
        )

        value = st.number_input(
            "Portfolio Value (USD)",
            min_value=0.0,
            value=50000.0,
            step=1000.0,
        )

        risk_profile = st.selectbox(
            "Risk Profile",
            ["conservative", "balanced", "aggressive"],
            index=1,
        )

        submitted = st.form_submit_button("Save Encrypted Portfolio")

    if submitted:
        portfolio_data = {
            "portfolio_id": portfolio_id,
            "owner": USER_NAME,
            "positions": [
                {"symbol": "VTI", "shares": 100},
                {"symbol": "VXUS", "shares": 50},
            ],
            "value": float(value),
            "currency": "USD",
            "risk_profile": risk_profile,
        }

        summary = save_portfolio(
            ctx=ctx,
            tenant_display_name=TENANT_NAME,
            user_display_name=USER_NAME,
            portfolio_id=portfolio_id,
            portfolio_data=portfolio_data,
            label=f"Tao Demo ({risk_profile})",
        )

        st.success("Portfolio saved and encrypted via SES-Core.")
        st.json(summary.to_dict())


def render_view_portfolios_page() -> None:
    st.subheader("View Portfolios (Decrypted via SES-Core)")

    st.write(
        f"""
        Showing portfolios for tenant: `{TENANT_NAME}`.

        Only summaries are loaded first.  
        Select a portfolio to view its **decrypted** contents.
        """
    )

    summaries = list_portfolios_for_tenant_as_dicts(ctx, TENANT_NAME)

    if not summaries:
        st.info("No portfolios found yet. Save one using 'Save Demo Portfolio'.")
        return

    st.write("**Portfolio Summaries:**")
    st.table(
        [
            {
                "Portfolio ID": s["portfolio_id"],
                "Label": s["label"],
                "Created": s["created_at"],
                "Updated": s["updated_at"],
                "User": s["user_display_name"],
            }
            for s in summaries
        ]
    )

    ids = [s["portfolio_id"] for s in summaries]
    selected_id = st.selectbox("Select portfolio to view details", ids)

    if st.button("Load and Decrypt Portfolio"):
        data = load_portfolio(
            ctx=ctx,
            tenant_display_name=TENANT_NAME,
            user_display_name=USER_NAME,
            portfolio_id=selected_id,
        )
        st.write("**Decrypted Portfolio JSON:**")
        st.json(data)


# ============================================================
# Page Routing
# ============================================================

if page == "Home":
    render_home_page()
elif page == "Save Demo Portfolio":
    render_save_demo_portfolio_page()
elif page == "View Portfolios":
    render_view_portfolios_page()
