import sys
import os
import pandas as pd
import plotly.express as px

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from graph import graph
from tools.data import get_unique_values, _df

st.set_page_config(page_title="Real Estate Assistant", page_icon="🏢", layout="wide")

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    div[data-testid="stForm"] { border: none; padding: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Real Estate Asset Manager")
st.caption("Analytics assistant — ask about P&L, property details, or comparisons.")


# ── shared helpers ─────────────────────────────────────────────────────────────

def _run_query(prompt: str) -> dict:
    return graph.invoke(
        {"question": prompt, "intent": "", "filters": {}, "data": None, "answer": "", "error": ""}
    )


def _to_df(result: dict) -> pd.DataFrame:
    data = result.get("data")
    if isinstance(data, list):
        return pd.DataFrame(data)
    if isinstance(data, dict):
        return pd.DataFrame({"property_name": list(data.keys()), "profit": list(data.values())})
    return pd.DataFrame()


def _render_widgets(result: dict) -> None:
    intent = result.get("intent")
    df = _to_df(result)

    if intent == "pl" and not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Profit", f"${df['profit'].sum():,.0f}")
        c2.metric("Properties", int(df["property_name"].nunique()))
        c3.metric("Ledger Types", int(df["ledger_type"].nunique()) if "ledger_type" in df else 0)
        if "ledger_type" in df.columns:
            tbl = (
                df.groupby("ledger_type", dropna=False)["profit"]
                .sum()
                .sort_values(ascending=False)
                .reset_index()
                .rename(columns={"ledger_type": "Ledger Type", "profit": "Profit ($)"})
            )
            tbl["Profit ($)"] = tbl["Profit ($)"].apply(lambda x: f"${x:,.0f}")
            st.dataframe(tbl, use_container_width=True, hide_index=True)

    elif intent == "compare" and not df.empty:
        ranked = df.sort_values("profit", ascending=False).reset_index(drop=True)
        cols = st.columns(len(ranked))
        for i, row in ranked.iterrows():
            cols[i].metric(str(row["property_name"]), f"${row['profit']:,.0f}")
        display = ranked.rename(columns={"property_name": "Property", "profit": "Profit ($)"}).copy()
        display["Profit ($)"] = display["Profit ($)"].apply(lambda x: f"${x:,.0f}")
        st.dataframe(display, use_container_width=True, hide_index=True)

    elif intent == "property" and not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Records", len(df))
        c2.metric("Tenants", int(df["tenant_name"].nunique()) if "tenant_name" in df else 0)
        c3.metric("Net Profit", f"${df['profit'].sum():,.0f}" if "profit" in df else "N/A")
        show_cols = [c for c in ["property_name", "tenant_name", "month", "ledger_type", "profit"] if c in df.columns]
        st.dataframe(df[show_cols].head(20), use_container_width=True, hide_index=True)


def _render_diagnostics(result: dict) -> None:
    df = _to_df(result)
    intent = result.get("intent", "unknown")
    icon = {"pl": "📊", "compare": "⚖️", "property": "🏠", "general": "💬", "clarify": "❓"}.get(intent, "🔍")
    st.write(f"**Intent:** {icon} `{intent}`")
    filters = result.get("filters") or {}
    if filters:
        for k, v in filters.items():
            st.write(f"- **{k}:** `{v}`")
    else:
        st.caption("No filters applied.")
    st.write(f"**Rows used:** `{len(df)}`")
    if result.get("error"):
        st.error(result["error"])


# ── dashboard helpers ──────────────────────────────────────────────────────────

def _dashboard_filter(df: pd.DataFrame, year: str, quarter: str, property_name: str, ledger_type: str) -> pd.DataFrame:
    if year != "All":
        df = df[df["year"].astype(str) == year]
    if quarter != "All":
        df = df[df["quarter"].astype(str) == quarter]
    if property_name != "All":
        df = df[df["property_name"].astype(str) == property_name]
    if ledger_type != "All":
        df = df[df["ledger_type"].astype(str) == ledger_type]
    return df


def _fmt(val: float) -> str:
    if abs(val) >= 1_000_000:
        return f"${val / 1_000_000:.2f}M"
    if abs(val) >= 1_000:
        return f"${val / 1_000:.1f}K"
    return f"${val:,.0f}"


# ── session state ──────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = ""


# ── tabs ───────────────────────────────────────────────────────────────────────

tab_dash, tab_assist = st.tabs(["📊 Dashboard", "💬 Assistant"])


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD TAB
# ══════════════════════════════════════════════════════════════════════════════

with tab_dash:

    # ── Filters ───────────────────────────────────────────────────────────────
    years_opts      = ["All"] + sorted([str(v) for v in get_unique_values("year")], reverse=True)
    quarters_opts   = ["All"] + sorted([str(v) for v in get_unique_values("quarter")], reverse=True)
    properties_opts = ["All"] + sorted([str(v) for v in get_unique_values("property_name")])
    lt_opts         = ["All", "revenue", "expenses"]

    fc1, fc2, fc3, fc4 = st.columns(4)
    sel_year     = fc1.selectbox("Year",         years_opts,      key="dash_year")
    sel_quarter  = fc2.selectbox("Quarter",      quarters_opts,   key="dash_quarter")
    sel_property = fc3.selectbox("Property",     properties_opts, key="dash_property")
    sel_lt       = fc4.selectbox("Ledger Type",  lt_opts,         key="dash_lt")

    filtered = _dashboard_filter(_df.copy(), sel_year, sel_quarter, sel_property, sel_lt)

    st.divider()

    # ── KPIs ──────────────────────────────────────────────────────────────────
    total_revenue  = filtered.loc[filtered["ledger_type"] == "revenue",  "profit"].sum()
    total_expenses = filtered.loc[filtered["ledger_type"] == "expenses", "profit"].sum()
    net_profit     = filtered["profit"].sum()
    n_properties   = int(filtered["property_name"].nunique())
    n_tenants      = int(filtered["tenant_name"].nunique())

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Revenue",    _fmt(total_revenue))
    k2.metric("Total Expenses",   _fmt(abs(total_expenses)))
    k3.metric("Net Profit / NOI", _fmt(net_profit))
    k4.metric("Properties",       n_properties)
    k5.metric("Tenants",          n_tenants)

    st.divider()

    # ── Charts ────────────────────────────────────────────────────────────────
    ch_left, ch_right = st.columns(2)

    # Top-left: Profit by Property
    with ch_left:
        st.subheader("Profit by Property")
        if not filtered.empty:
            by_prop = (
                filtered.groupby("property_name", dropna=False)["profit"]
                .sum()
                .reset_index()
                .sort_values("profit", ascending=True)
            )
            fig = px.bar(
                by_prop,
                x="profit",
                y="property_name",
                orientation="h",
                labels={"profit": "Profit ($)", "property_name": "Property"},
                color="profit",
                color_continuous_scale=["#d73027", "#fee08b", "#1a9850"],
                color_continuous_midpoint=0,
            )
            fig.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=10, b=0), height=320)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data for the selected filters.")

    # Top-right: Revenue vs Expenses by Month
    with ch_right:
        st.subheader("Revenue vs Expenses by Month")
        if not filtered.empty:
            by_month = (
                filtered.groupby(["month", "ledger_type"], dropna=False)["profit"]
                .sum()
                .reset_index()
                .sort_values("month")
            )
            fig2 = px.bar(
                by_month,
                x="month",
                y="profit",
                color="ledger_type",
                barmode="group",
                labels={"profit": "Amount ($)", "month": "Month", "ledger_type": "Type"},
                color_discrete_map={"revenue": "#1a9850", "expenses": "#d73027"},
            )
            fig2.update_layout(
                legend_title_text="",
                margin=dict(l=0, r=0, t=10, b=0),
                height=320,
                xaxis_tickangle=-45,
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No data for the selected filters.")

    bl_left, bl_right = st.columns(2)

    # Bottom-left: Profit by Ledger Group
    with bl_left:
        st.subheader("Profit by Ledger Group")
        if not filtered.empty:
            by_group = (
                filtered.groupby("ledger_group", dropna=False)["profit"]
                .sum()
                .reset_index()
                .sort_values("profit", ascending=True)
            )
            fig3 = px.bar(
                by_group,
                x="profit",
                y="ledger_group",
                orientation="h",
                labels={"profit": "Profit ($)", "ledger_group": "Ledger Group"},
                color="profit",
                color_continuous_scale=["#d73027", "#fee08b", "#1a9850"],
                color_continuous_midpoint=0,
            )
            fig3.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=10, b=0), height=320)
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No data for the selected filters.")

    # Bottom-right: Monthly Net Profit Trend
    with bl_right:
        st.subheader("Monthly Net Profit Trend")
        if not filtered.empty:
            trend = (
                filtered.groupby("month", dropna=False)["profit"]
                .sum()
                .reset_index()
                .sort_values("month")
            )
            fig4 = px.line(
                trend,
                x="month",
                y="profit",
                markers=True,
                labels={"profit": "Net Profit ($)", "month": "Month"},
            )
            fig4.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)
            fig4.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=320, xaxis_tickangle=-45)
            fig4.update_traces(line_color="#2c7bb6", marker_color="#2c7bb6")
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("No data for the selected filters.")


# ══════════════════════════════════════════════════════════════════════════════
# ASSISTANT TAB
# ══════════════════════════════════════════════════════════════════════════════

with tab_assist:
    left, center, right = st.columns([1.1, 2.4, 1.2], gap="large")

    # ── LEFT: guided input ────────────────────────────────────────────────────
    with left:
        st.subheader("Guided Input")
        properties = ["All"] + sorted([str(v) for v in get_unique_values("property_name")])
        years      = ["Any"] + sorted([str(v) for v in get_unique_values("year")])
        quarters   = ["Any"] + sorted([str(v) for v in get_unique_values("quarter")])
        prop_sel   = st.selectbox("Property", properties, key="assist_prop")
        year_sel   = st.selectbox("Year",     years,      key="assist_year")
        qtr_sel    = st.selectbox("Quarter",  quarters,   key="assist_quarter")
        action     = st.selectbox("Question Type", ["P&L Summary", "Property Details", "Compare Two Properties"])

        if st.button("Build Question", use_container_width=True):
            ptxt = prop_sel if prop_sel != "All" else "all properties"
            ytxt = year_sel if year_sel != "Any" else "latest year"
            qtxt = qtr_sel  if qtr_sel  != "Any" else ""
            if action == "Compare Two Properties":
                lp = prop_sel if prop_sel != "All" else "Building 180"
                st.session_state.pending_prompt = f"Compare {lp} vs Building 140 in {ytxt}."
            elif action == "Property Details":
                st.session_state.pending_prompt = f"Show property details for {ptxt} in {ytxt} {qtxt}."
            else:
                st.session_state.pending_prompt = f"What is the P&L for {ptxt} in {ytxt} {qtxt}?"

        st.divider()
        st.caption("Quick demo prompts")
        samples = [
            "What is total P&L for Building 180 in 2025?",
            "Compare Building 180 vs Building 140 in 2025.",
            "Show tenant-level details for Building 140 in 2025 Q1.",
        ]
        for idx, q in enumerate(samples):
            if st.button(q, key=f"sample_{idx}", use_container_width=True):
                st.session_state.pending_prompt = q

    # ── CENTER: chat window ───────────────────────────────────────────────────
    with center:
        st.subheader("Assistant")

        msg_window = st.container(height=510, border=True)
        with msg_window:
            if not st.session_state.messages:
                st.markdown(
                    "<div style='text-align:center;color:#888;padding:3rem 0;font-size:0.9rem'>"
                    "No messages yet — type below or use the guided input on the left."
                    "</div>",
                    unsafe_allow_html=True,
                )
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    if msg["role"] == "assistant" and "result" in msg:
                        _render_widgets(msg["result"])

        with st.form("chat_form", clear_on_submit=True):
            inp_col, btn_col = st.columns([8, 1])
            with inp_col:
                typed = st.text_input(
                    "msg", placeholder="Ask about your portfolio...",
                    label_visibility="collapsed",
                )
            with btn_col:
                submitted = st.form_submit_button("Send ↵", use_container_width=True)

        prompt = st.session_state.pending_prompt or (typed.strip() if submitted else "")

        if prompt:
            st.session_state.pending_prompt = ""
            st.session_state.messages.append({"role": "user", "content": prompt})

            with msg_window:
                with st.chat_message("user"):
                    st.markdown(prompt)
                with st.spinner("Analyzing portfolio data..."):
                    result = _run_query(prompt)
                answer = result.get("answer", "").strip() or "I could not generate a response."
                with st.chat_message("assistant"):
                    st.markdown(answer)
                    _render_widgets(result)

            st.session_state.messages.append({"role": "assistant", "content": answer, "result": result})

    # ── RIGHT: diagnostics ────────────────────────────────────────────────────
    with right:
        st.subheader("Diagnostics")
        assistants = [m for m in st.session_state.messages if m.get("role") == "assistant" and "result" in m]
        if assistants:
            _render_diagnostics(assistants[-1]["result"])
        else:
            st.info("Run a question to see intent, filters, and row count.")
