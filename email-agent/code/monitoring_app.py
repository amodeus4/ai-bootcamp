"""Monitoring dashboard for Email Agent - view logs, evaluations, and feedback."""

from __future__ import annotations
import os
import json
from typing import Optional
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from monitoring.db import Database

# Load environment variables
load_dotenv()


def get_db() -> Database:
    """Get or create database connection."""
    if "db" not in st.session_state:
        db_url = os.getenv("DATABASE_URL", "sqlite:///email_agent_monitoring.db")
        st.session_state.db = Database(db_url)
        st.session_state.db.ensure_schema()
    return st.session_state.db


def main():
    st.set_page_config(
        page_title="📊 Email Agent Monitor", page_icon="📊", layout="wide"
    )

    st.title("📊 Email Agent Monitoring Dashboard")
    st.caption("View logs, evaluation results, and add feedback")

    db = get_db()

    # Sidebar filters
    with st.sidebar:
        st.subheader("🔍 Filters")
        limit = st.number_input(
            "Max logs to show", min_value=10, max_value=500, value=50
        )

        st.divider()

        # Database info
        st.subheader("📁 Database")
        db_url = os.getenv("DATABASE_URL", "sqlite:///email_agent_monitoring.db")
        st.code(db_url, language=None)

        if st.button("🔄 Refresh"):
            st.rerun()

    # Get stats
    stats = db.get_stats()

    # Summary metrics
    st.subheader("📈 Overview")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Conversations", stats["total_conversations"])
    with col2:
        success_rate = (
            stats["successful_conversations"] / max(stats["total_conversations"], 1)
        ) * 100
        st.metric("Success Rate", f"{success_rate:.0f}%")
    with col3:
        st.metric("Avg Duration", f"{stats['avg_duration_ms']:.0f}ms")
    with col4:
        st.metric("Avg Eval Score", f"{stats['avg_eval_score']:.0%}")
    with col5:
        total_fb = stats["positive_feedback"] + stats["negative_feedback"]
        if total_fb > 0:
            pos_rate = stats["positive_feedback"] / total_fb * 100
            st.metric(
                "Positive Feedback",
                f"{pos_rate:.0f}%",
                delta=f"{stats['positive_feedback']}/{total_fb}",
            )
        else:
            st.metric("Feedback", "No feedback yet")

    st.divider()

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📝 Logs", "📊 Analytics", "💬 Feedback"])

    with tab1:
        render_logs_tab(db, limit)

    with tab2:
        render_analytics_tab(db, limit)

    with tab3:
        render_feedback_tab(db)


def render_logs_tab(db: Database, limit: int):
    """Render the logs tab."""
    st.subheader("Recent Conversations")

    logs = db.list_logs(limit=limit)

    if not logs:
        st.info("No logs found. Start using the email agent to generate logs!")
        return

    # Create selection list
    options = []
    for log in logs:
        prompt_preview = (
            (log.get("user_prompt", "")[:50] + "...")
            if len(log.get("user_prompt", "")) > 50
            else log.get("user_prompt", "")
        )
        label = (
            f"#{log['id']} | {str(log.get('created_at', ''))[:19]} | {prompt_preview}"
        )
        options.append((log["id"], label))

    selected_label = st.selectbox(
        "Select a conversation", options=[lbl for _, lbl in options]
    )
    selected_id = next(
        (id_ for id_, lbl in options if lbl == selected_label), options[0][0]
    )

    # Load selected log
    log = db.get_log(selected_id)
    checks = db.get_checks(selected_id)
    feedbacks = db.get_feedback(selected_id)

    # Display log details
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Duration", f"{log.get('duration_ms', 0)}ms")
    with col2:
        st.metric("Model", log.get("model", "N/A"))
    with col3:
        status = "✅ Success" if log.get("success", True) else "❌ Failed"
        st.metric("Status", status)
    with col4:
        st.metric("Created", str(log.get("created_at", ""))[:19])

    # User prompt
    with st.expander("💬 User Prompt", expanded=True):
        st.code(log.get("user_prompt", ""), language=None)

    # Assistant response
    with st.expander("🤖 Assistant Response", expanded=True):
        st.write(log.get("assistant_answer", ""))

    # Tool calls
    with st.expander("🔧 Tool Calls", expanded=False):
        try:
            tool_calls = json.loads(log.get("tool_calls", "[]"))
            if tool_calls:
                for call in tool_calls:
                    st.code(
                        f"{call.get('tool', 'unknown')}({json.dumps(call.get('args', {}))})",
                        language=None,
                    )
            else:
                st.info("No tool calls")
        except:
            st.info("No tool calls")

    # Evaluation checks
    st.markdown("**📊 Evaluation Checks**")
    if checks:
        check_data = []
        for c in checks:
            check_data.append(
                {
                    "Check": c.get("check_name", "").replace("_", " ").title(),
                    "Passed": "✅" if c.get("passed") else "❌",
                    "Score": f"{c.get('score', 0):.0%}"
                    if c.get("score") is not None
                    else "N/A",
                    "Details": c.get("details", ""),
                }
            )
        st.dataframe(check_data, use_container_width=True)
    else:
        st.info("No evaluation checks")

    # Existing feedback
    st.markdown("**💬 Feedback**")
    if feedbacks:
        for fb in feedbacks:
            icon = "👍" if fb.get("is_good") else "👎"
            st.write(
                f"{icon} {fb.get('comments', 'No comment')} - {str(fb.get('created_at', ''))[:19]}"
            )
    else:
        st.info("No feedback yet")

    # Add feedback form
    st.markdown("**Add Feedback:**")
    with st.form(f"feedback_form_{selected_id}", clear_on_submit=True):
        col1, col2 = st.columns([1, 3])
        with col1:
            is_good = st.radio("Rating", ["👍 Good", "👎 Bad"], horizontal=True)
        with col2:
            comments = st.text_input("Comments (optional)")

        ref_answer = st.text_area(
            "Reference Answer (optional)",
            placeholder="What should the correct answer be?",
        )

        if st.form_submit_button("Submit Feedback"):
            good_flag = is_good.startswith("👍")
            db.insert_feedback(
                selected_id,
                is_good=good_flag,
                comments=comments or None,
                reference_answer=ref_answer or None,
            )
            st.success("✅ Feedback saved!")
            st.rerun()


def render_analytics_tab(db: Database, limit: int):
    """Render analytics tab with charts."""
    st.subheader("📊 Analytics")

    logs = db.list_logs(limit=limit)

    if not logs:
        st.info("No data for analytics yet")
        return

    # Convert to DataFrame
    df = pd.DataFrame(logs)

    # Duration over time
    if "duration_ms" in df.columns and "created_at" in df.columns:
        st.markdown("### ⏱️ Response Duration Over Time")
        df["created_at"] = pd.to_datetime(df["created_at"])
        df_sorted = df.sort_values("created_at")
        st.line_chart(df_sorted.set_index("created_at")["duration_ms"])

    # Success rate
    if "success" in df.columns:
        st.markdown("### ✅ Success Rate")
        success_counts = df["success"].value_counts()
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Successful", int(success_counts.get(1, 0)))
        with col2:
            st.metric("Failed", int(success_counts.get(0, 0)))

    # Check pass rates
    st.markdown("### 📋 Evaluation Check Pass Rates")
    all_checks = []
    for log in logs:
        checks = db.get_checks(log["id"])
        all_checks.extend(checks)

    if all_checks:
        check_df = pd.DataFrame(all_checks)
        if "check_name" in check_df.columns and "passed" in check_df.columns:
            pass_rates = check_df.groupby("check_name")["passed"].mean()
            st.bar_chart(pass_rates)

            # Detailed breakdown
            st.markdown("**Detailed Breakdown:**")
            breakdown = (
                check_df.groupby("check_name")
                .agg({"passed": ["sum", "count", "mean"], "score": "mean"})
                .round(2)
            )
            breakdown.columns = ["Passed", "Total", "Pass Rate", "Avg Score"]
            st.dataframe(breakdown, use_container_width=True)


def render_feedback_tab(db: Database):
    """Render feedback summary tab."""
    st.subheader("💬 Feedback Summary")

    logs = db.list_logs(limit=200)

    positive_logs = []
    negative_logs = []

    for log in logs:
        feedbacks = db.get_feedback(log["id"])
        for fb in feedbacks:
            entry = {
                "log_id": log["id"],
                "prompt": log.get("user_prompt", "")[:100],
                "comments": fb.get("comments", ""),
                "created_at": fb.get("created_at", ""),
            }
            if fb.get("is_good"):
                positive_logs.append(entry)
            else:
                negative_logs.append(entry)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 👍 Positive Feedback")
        if positive_logs:
            for entry in positive_logs[:10]:
                with st.expander(f"#{entry['log_id']}: {entry['prompt'][:40]}..."):
                    st.write(f"**Comment:** {entry['comments'] or 'No comment'}")
                    st.caption(str(entry["created_at"])[:19])
        else:
            st.info("No positive feedback yet")

    with col2:
        st.markdown("### 👎 Negative Feedback")
        if negative_logs:
            for entry in negative_logs[:10]:
                with st.expander(f"#{entry['log_id']}: {entry['prompt'][:40]}..."):
                    st.write(f"**Comment:** {entry['comments'] or 'No comment'}")
                    st.caption(str(entry["created_at"])[:19])
        else:
            st.info("No negative feedback yet")

    # Export option
    st.divider()
    st.markdown("### 📥 Export Data")

    if st.button("Export Feedback to CSV"):
        all_feedback = positive_logs + negative_logs
        if all_feedback:
            df = pd.DataFrame(all_feedback)
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="email_agent_feedback.csv",
                mime="text/csv",
            )
        else:
            st.warning("No feedback to export")


if __name__ == "__main__":
    main()
