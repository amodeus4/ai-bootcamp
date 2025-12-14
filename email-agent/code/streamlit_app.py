"""Streamlit app for Email Agent with monitoring."""

import os
import json
import queue
import threading
import time
from datetime import datetime
from typing import List, Optional
import streamlit as st
from dotenv import load_dotenv

from email_agent import (
    EmailAgent,
    authenticate_gmail,
    ElasticsearchEmailStore,
    GmailFetchTool,
    ElasticsearchSearchTool,
    ElasticsearchWriteTool,
    ConversationHistoryTool,
    SearchAttachmentsTool,
    CategorizeEmailsTool,
    PriorityInboxTool,
    fetch_and_index_all_emails,
)
from monitoring.db import Database
from monitoring.schemas import ConversationLog, CheckResult, CheckName


# Load environment variables
load_dotenv()


def get_db() -> Database:
    """Get or create database connection."""
    if "db" not in st.session_state:
        db_url = os.getenv("DATABASE_URL", "sqlite:///email_agent_monitoring.db")
        st.session_state.db = Database(db_url)
        st.session_state.db.ensure_schema()
    return st.session_state.db


def init_agent():
    """Initialize the email agent and related services."""
    if "agent" in st.session_state:
        return (
            st.session_state.agent,
            st.session_state.es_store,
            st.session_state.gmail_service,
        )

    # Configuration
    es_host = os.getenv("ES_HOST", "localhost")
    es_port = int(os.getenv("ES_PORT", "9200"))
    es_index = os.getenv("ES_INDEX_NAME", "emails")
    credentials_file = os.getenv("CREDENTIALS_FILE", "credentials.json")

    # Initialize Gmail API
    try:
        gmail_service = authenticate_gmail(credentials_file)
    except Exception as e:
        st.error(f"❌ Gmail authentication failed: {e}")
        st.stop()

    # Initialize Elasticsearch
    try:
        es_store = ElasticsearchEmailStore(
            es_host=es_host, es_port=es_port, index_name=es_index
        )
    except Exception as e:
        st.error(f"❌ Elasticsearch connection failed: {e}")
        st.info("Make sure Elasticsearch is running: `docker start elasticsearch`")
        st.stop()

    # Create tools
    gmail_tool = GmailFetchTool(gmail_service)
    search_tool = ElasticsearchSearchTool(es_store)
    write_tool = ElasticsearchWriteTool(es_store)
    conversation_tool = ConversationHistoryTool(es_store)
    attachment_tool = SearchAttachmentsTool(es_store)
    categorize_tool = CategorizeEmailsTool(es_store)
    priority_tool = PriorityInboxTool(es_store)

    # Create agent
    agent = EmailAgent(
        tools=[
            gmail_tool,
            search_tool,
            write_tool,
            conversation_tool,
            attachment_tool,
            categorize_tool,
            priority_tool,
        ]
    )

    # Store in session state
    st.session_state.agent = agent
    st.session_state.es_store = es_store
    st.session_state.gmail_service = gmail_service

    return agent, es_store, gmail_service


def init_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "tool_calls" not in st.session_state:
        st.session_state.tool_calls = []


def run_agent_with_logging(agent: EmailAgent, user_input: str, db: Database) -> dict:
    """Run agent and log the interaction."""
    start_time = time.time()
    tool_calls_made = []

    # Capture tool calls by wrapping the agent's tools
    original_tools = agent.tools.copy()

    def wrap_tool(tool_name, tool):
        original_run = tool.run

        def wrapped_run(*args, **kwargs):
            tool_calls_made.append(
                {
                    "tool": tool_name,
                    "args": kwargs,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return original_run(*args, **kwargs)

        tool.run = wrapped_run
        return tool

    # Wrap tools to capture calls
    for name, tool in agent.tools.items():
        wrap_tool(name, tool)

    # Run the agent
    try:
        response = agent.chat(user_input)
        success = True
        error = None
    except Exception as e:
        response = f"Error: {str(e)}"
        success = False
        error = str(e)

    end_time = time.time()
    duration_ms = int((end_time - start_time) * 1000)

    # Log to database
    log_record = ConversationLog(
        user_prompt=user_input,
        assistant_answer=response,
        tool_calls=json.dumps(tool_calls_made),
        model="gpt-4o-mini",
        provider="openai",
        duration_ms=duration_ms,
        success=success,
        error=error,
    )

    log_id = db.insert_log(log_record)

    # Run basic evaluations
    checks = evaluate_response(log_id, user_input, response, tool_calls_made)
    db.insert_checks(checks)

    return {
        "response": response,
        "tool_calls": tool_calls_made,
        "log_id": log_id,
        "duration_ms": duration_ms,
        "checks": checks,
    }


def evaluate_response(
    log_id: int, prompt: str, response: str, tool_calls: List[dict]
) -> List[CheckResult]:
    """Run basic rule-based evaluations on the response."""
    checks = []

    # Check 1: Response not empty
    checks.append(
        CheckResult(
            log_id=log_id,
            check_name=CheckName.response_not_empty,
            passed=bool(response and len(response.strip()) > 10),
            score=1.0 if response and len(response.strip()) > 10 else 0.0,
            details="Response has content" if response else "Empty response",
        )
    )

    # Check 2: Tool was called (for most queries)
    tool_called = len(tool_calls) > 0
    checks.append(
        CheckResult(
            log_id=log_id,
            check_name=CheckName.tool_called,
            passed=tool_called,
            score=1.0 if tool_called else 0.0,
            details=f"Tools called: {[t['tool'] for t in tool_calls]}"
            if tool_called
            else "No tools called",
        )
    )

    # Check 3: Response relevance (basic keyword check)
    prompt_words = set(prompt.lower().split())
    response_words = set(response.lower().split())
    common_words = prompt_words.intersection(response_words) - {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "to",
        "from",
        "in",
        "on",
        "at",
        "for",
        "of",
        "with",
        "my",
        "me",
        "i",
        "you",
        "your",
    }
    relevance_score = min(len(common_words) / max(len(prompt_words), 1), 1.0)
    checks.append(
        CheckResult(
            log_id=log_id,
            check_name=CheckName.response_relevant,
            passed=relevance_score > 0.1,
            score=relevance_score,
            details=f"Relevance score: {relevance_score:.2f}",
        )
    )

    # Check 4: No error in response
    has_error = "error" in response.lower() and (
        "failed" in response.lower() or "could not" in response.lower()
    )
    checks.append(
        CheckResult(
            log_id=log_id,
            check_name=CheckName.no_error,
            passed=not has_error,
            score=0.0 if has_error else 1.0,
            details="No errors detected"
            if not has_error
            else "Error detected in response",
        )
    )

    return checks


def render_tool_calls(tool_calls: List[dict]):
    """Render tool calls in a nice format."""
    if not tool_calls:
        st.info("No tools were called")
        return

    for i, call in enumerate(tool_calls, 1):
        tool_name = call.get("tool", "unknown")
        args = call.get("args", {})

        # Format arguments nicely
        args_display = []
        for k, v in args.items():
            if v is not None:
                args_display.append(f"{k}={repr(v)}")

        args_str = ", ".join(args_display) if args_display else ""
        st.code(f"🔧 {tool_name}({args_str})", language=None)


def render_checks(checks: List[CheckResult]):
    """Render evaluation checks."""
    if not checks:
        return

    cols = st.columns(len(checks))
    for i, check in enumerate(checks):
        with cols[i]:
            icon = "✅" if check.passed else "❌"
            st.metric(
                label=check.check_name.value.replace("_", " ").title(),
                value=icon,
                delta=f"{check.score:.0%}" if check.score is not None else None,
            )


def main():
    st.set_page_config(page_title="Email Agent", page_icon="", layout="wide")

    st.title("Email Agent")
    st.caption("Chat with your Gmail inbox using AI")

    # Initialize
    init_state()
    db = get_db()

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")

        # Initialize agent button
        if st.button("Initialize Agent", type="primary"):
            with st.spinner("Initializing..."):
                try:
                    agent, es_store, gmail_service = init_agent()
                    st.success("Agent initialized!")
                except Exception as e:
                    st.error(f"Failed: {e}")

        # Index emails button
        if "agent" in st.session_state:
            st.divider()
            st.subheader("Email Indexing")
            max_emails = st.number_input(
                "Max emails to index", min_value=10, max_value=200, value=50
            )
            if st.button("🔄 Re-index Emails"):
                with st.spinner(f"Indexing up to {max_emails} emails..."):
                    try:
                        indexed = fetch_and_index_all_emails(
                            st.session_state.gmail_service,
                            st.session_state.es_store,
                            max_emails=max_emails,
                        )
                        st.success(f" Indexed {len(indexed)} emails")
                    except Exception as e:
                        st.error(f"Failed: {e}")

        st.divider()
        st.subheader("📊 Monitoring")
        if st.button("📈 View Logs"):
            st.session_state.show_monitoring = True

        st.divider()
        st.subheader("💡 Example Queries")
        examples = [
            "Show me my unread emails",
            "Find emails from last week",
            "Search for invoices",
            "Show emails with attachments",
            "Find emails from my boss",
        ]
        for example in examples:
            if st.button(example, key=f"ex_{example}"):
                st.session_state.pending_query = example

        # Clear chat button
        st.divider()
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.session_state.tool_calls = []
            st.rerun()

    # Main chat area
    if "agent" not in st.session_state:
        st.info("👆 Click 'Initialize Agent' in the sidebar to get started")
        st.markdown("""
        ### Prerequisites
        1. **Gmail API**: Ensure `credentials.json` is in the code directory
        2. **Elasticsearch**: Run `docker start elasticsearch`
        3. **OpenAI API Key**: Set in `.env` file
        """)
        return

    agent = st.session_state.agent

    # Show monitoring panel if requested
    if st.session_state.get("show_monitoring"):
        render_monitoring_panel(db)
        if st.button("← Back to Chat"):
            st.session_state.show_monitoring = False
            st.rerun()
        return

    # Render chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("tool_calls"):
                with st.expander("🔧 Tool Calls", expanded=False):
                    render_tool_calls(msg["tool_calls"])
            if msg["role"] == "assistant" and msg.get("checks"):
                with st.expander("📊 Evaluation", expanded=False):
                    render_checks(msg["checks"])

    # Handle pending query from sidebar
    if "pending_query" in st.session_state:
        prompt = st.session_state.pending_query
        del st.session_state.pending_query
    else:
        prompt = st.chat_input("Ask about your emails...")

    if prompt:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = run_agent_with_logging(agent, prompt, db)

            st.markdown(result["response"])

            with st.expander("🔧 Tool Calls", expanded=True):
                render_tool_calls(result["tool_calls"])

            with st.expander("📊 Evaluation", expanded=False):
                render_checks(result["checks"])

            st.caption(f"⏱️ {result['duration_ms']}ms | Log ID: {result['log_id']}")

        # Save to history
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": result["response"],
                "tool_calls": result["tool_calls"],
                "checks": result["checks"],
                "log_id": result["log_id"],
            }
        )


def render_monitoring_panel(db: Database):
    """Render the monitoring/logs panel."""
    st.header("📊 Monitoring Dashboard")

    # Get recent logs
    logs = db.list_logs(limit=50)

    if not logs:
        st.info("No logs yet. Start chatting to generate logs!")
        return

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Conversations", len(logs))
    with col2:
        successful = sum(1 for log in logs if log.get("success", True))
        st.metric("Successful", f"{successful}/{len(logs)}")
    with col3:
        avg_duration = sum(log.get("duration_ms", 0) for log in logs) / max(
            len(logs), 1
        )
        st.metric("Avg Duration", f"{avg_duration:.0f}ms")
    with col4:
        # Calculate avg eval score
        all_checks = []
        for log in logs:
            checks = db.get_checks(log["id"])
            all_checks.extend(checks)
        if all_checks:
            avg_score = sum(
                c.get("score", 0) for c in all_checks if c.get("score")
            ) / len(all_checks)
            st.metric("Avg Eval Score", f"{avg_score:.0%}")
        else:
            st.metric("Avg Eval Score", "N/A")

    st.divider()

    # Log list
    st.subheader("Recent Conversations")

    for log in logs[:20]:
        with st.expander(
            f"#{log['id']} - {str(log.get('created_at', ''))[:19]}", expanded=False
        ):
            st.markdown("**User Query:**")
            st.code(log.get("user_prompt", ""), language=None)

            st.markdown("**Assistant Response:**")
            st.write(
                log.get("assistant_answer", "")[:500] + "..."
                if len(log.get("assistant_answer", "")) > 500
                else log.get("assistant_answer", "")
            )

            st.markdown("**Tool Calls:**")
            try:
                tool_calls = json.loads(log.get("tool_calls", "[]"))
                render_tool_calls(tool_calls)
            except:
                st.write("None")

            st.markdown("**Evaluation Checks:**")
            checks = db.get_checks(log["id"])
            if checks:
                check_df = [
                    {
                        "Check": c.get("check_name", "").replace("_", " ").title(),
                        "Passed": "✅" if c.get("passed") else "❌",
                        "Score": f"{c.get('score', 0):.0%}"
                        if c.get("score") is not None
                        else "N/A",
                        "Details": c.get("details", ""),
                    }
                    for c in checks
                ]
                st.dataframe(check_df, use_container_width=True)
            else:
                st.info("No checks")

            # Feedback form
            st.markdown("**Feedback:**")
            feedbacks = db.get_feedback(log["id"])
            if feedbacks:
                for fb in feedbacks:
                    icon = "👍" if fb.get("is_good") else "👎"
                    st.write(f"{icon} {fb.get('comments', 'No comment')}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("👍 Good", key=f"good_{log['id']}"):
                    db.insert_feedback(
                        log["id"], is_good=True, comments="Marked good via UI"
                    )
                    st.success("Feedback saved!")
                    st.rerun()
            with col2:
                if st.button("👎 Bad", key=f"bad_{log['id']}"):
                    db.insert_feedback(
                        log["id"], is_good=False, comments="Marked bad via UI"
                    )
                    st.success("Feedback saved!")
                    st.rerun()


if __name__ == "__main__":
    main()
