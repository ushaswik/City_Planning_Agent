"""
Streamlit frontend for the Municipal Multi-Agent System.

Run:
  streamlit run frontend/streamlit_app.py
"""

from __future__ import annotations

import asyncio
import os
from contextlib import redirect_stdout
from io import StringIO
from typing import Any

import pandas as pd
import streamlit as st

from municipal_agents.context import MunicipalContext
from municipal_agents.database import DB_PATH, clear_agent_outputs, init_database, seed_sample_data
from municipal_agents.pipeline import run_interactive_stage, run_municipal_pipeline


def _ensure_session_defaults() -> None:
    if "db_path" not in st.session_state:
        st.session_state.db_path = DB_PATH
    if "city_name" not in st.session_state:
        st.session_state.city_name = "Metroville"
    if "quarterly_budget" not in st.session_state:
        st.session_state.quarterly_budget = 75_000_000.0
    if "planning_horizon_weeks" not in st.session_state:
        st.session_state.planning_horizon_weeks = 12
    if "last_run_output" not in st.session_state:
        st.session_state.last_run_output = ""


def _make_context() -> MunicipalContext:
    ctx = MunicipalContext()
    ctx.db_path = st.session_state.db_path
    ctx.city_name = st.session_state.city_name
    ctx.quarterly_budget = float(st.session_state.quarterly_budget)
    ctx.planning_horizon_weeks = int(st.session_state.planning_horizon_weeks)
    return ctx


def _capture_async(fn, *args, **kwargs) -> tuple[str, Any]:
    """
    Run an async function and capture stdout.
    Returns (stdout, result).
    """
    buf = StringIO()
    with redirect_stdout(buf):
        result = asyncio.run(fn(*args, **kwargs))
    return buf.getvalue(), result


def _db_exists(db_path: str) -> bool:
    return os.path.exists(db_path)


def _as_df(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


st.set_page_config(page_title="Municipal Pipeline Dashboard", layout="wide")
_ensure_session_defaults()

st.title("Municipal Multi-Agent Pipeline")

with st.sidebar:
    st.subheader("Configuration")
    st.session_state.db_path = st.text_input("SQLite DB path", value=st.session_state.db_path)
    st.session_state.city_name = st.text_input("City name", value=st.session_state.city_name)
    st.session_state.quarterly_budget = st.number_input(
        "Quarterly budget (USD)",
        min_value=0.0,
        value=float(st.session_state.quarterly_budget),
        step=1_000_000.0,
        format="%.0f",
    )
    st.session_state.planning_horizon_weeks = st.number_input(
        "Planning horizon (weeks)",
        min_value=1,
        max_value=104,
        value=int(st.session_state.planning_horizon_weeks),
        step=1,
    )

    st.divider()
    st.subheader("Database")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Init + seed sample data", use_container_width=True):
            init_database(st.session_state.db_path)
            seed_sample_data(st.session_state.db_path)
            st.success("Database initialized and sample data seeded.")
    with col_b:
        if st.button("Clear agent outputs", use_container_width=True):
            clear_agent_outputs(st.session_state.db_path)
            st.success("Agent outputs cleared.")

    st.divider()
    st.subheader("Pipeline")
    if not os.environ.get("OPENAI_API_KEY"):
        st.warning("OPENAI_API_KEY is not set. Browsing works; running agents will fail.")

    stage = st.selectbox("Run stage", ["full", "formation", "governance", "scheduling"])
    reset_data = st.checkbox("Reset agent outputs before run", value=True)
    verbose = st.checkbox("Verbose (capture prints)", value=True)
    run_btn = st.button("Run", type="primary", use_container_width=True)

if run_btn:
    ctx = _make_context()
    if reset_data:
        clear_agent_outputs(ctx.db_path)
    try:
        if stage == "full":
            stdout, result = _capture_async(run_municipal_pipeline, ctx, False, verbose)
            st.session_state.last_run_output = (stdout or "") + "\n" + str(result.get("formation", "")) + "\n\n" + str(
                result.get("governance", "")
            ) + "\n\n" + str(result.get("scheduling", ""))
        else:
            stdout, result = _capture_async(run_interactive_stage, stage, ctx, None, verbose)
            st.session_state.last_run_output = (stdout or "") + "\n" + str(result)
    except Exception as e:
        st.session_state.last_run_output = f"Error: {e}"


ctx = _make_context()

top_left, top_right = st.columns([1, 2])
with top_left:
    st.subheader("System state")
    if not _db_exists(ctx.db_path):
        st.error(f"Database not found at `{ctx.db_path}`. Use 'Init + seed sample data'.")
    else:
        summary = ctx.get_system_summary()
        st.metric("Open issues", summary["open_issues"])
        st.metric("Project candidates", summary["project_candidates"])
        st.metric("Approved projects", summary["approved_projects"])
        st.metric("Scheduled tasks", summary["scheduled_tasks"])
        st.metric("Budget allocated", f"${summary['total_allocated']:,.0f}")
        st.metric("Budget remaining", f"${(summary['quarterly_budget'] - summary['total_allocated']):,.0f}")

with top_right:
    st.subheader("Last run output")
    st.code(st.session_state.last_run_output or "No runs yet.", language="text")


st.divider()
tab_overview, tab_issues, tab_candidates, tab_decisions, tab_schedule, tab_resources, tab_audit = st.tabs(
    ["Overview", "Issues", "Candidates", "Decisions", "Schedule", "Resources", "Audit log"]
)

with tab_overview:
    if _db_exists(ctx.db_path):
        st.write("This dashboard reflects the current SQLite database state.")
        issues = ctx.get_open_issues()
        candidates = ctx.get_project_candidates()
        decisions = ctx.get_portfolio_decisions()
        tasks = ctx.get_schedule_tasks()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Open issues", len(issues))
        c2.metric("Candidates", len(candidates))
        c3.metric("Decisions", len(decisions))
        c4.metric("Schedule tasks", len(tasks))

with tab_issues:
    if _db_exists(ctx.db_path):
        df = _as_df(ctx.get_open_issues())
        st.dataframe(df, use_container_width=True, hide_index=True)

with tab_candidates:
    if _db_exists(ctx.db_path):
        df = _as_df(ctx.get_project_candidates())
        st.dataframe(df, use_container_width=True, hide_index=True)

with tab_decisions:
    if _db_exists(ctx.db_path):
        df = _as_df(ctx.get_portfolio_decisions())
        st.dataframe(df, use_container_width=True, hide_index=True)

with tab_schedule:
    if _db_exists(ctx.db_path):
        df = _as_df(ctx.get_schedule_tasks())
        st.dataframe(df, use_container_width=True, hide_index=True)

with tab_resources:
    if _db_exists(ctx.db_path):
        df = _as_df(ctx.get_resource_calendar())
        st.dataframe(df, use_container_width=True, hide_index=True)

with tab_audit:
    if _db_exists(ctx.db_path):
        rows = ctx.query("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 200")
        df = _as_df(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

