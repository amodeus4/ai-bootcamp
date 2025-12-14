"""Database layer for email agent monitoring."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import List, Optional

from .schemas import ConversationLog, CheckResult, Feedback


class Database:
    """Lightweight DB layer with SQLite support."""

    def __init__(self, database_url: Optional[str] = None) -> None:
        self.database_url = database_url or os.environ.get("DATABASE_URL")
        if not self.database_url:
            self.database_url = "sqlite:///email_agent_monitoring.db"

        self._conn = None

    def connect(self):
        if self._conn:
            return self._conn

        if self.database_url.startswith("sqlite://"):
            db_path = self.database_url.split("sqlite:///")[-1]
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON;")
        else:
            raise ValueError(f"Unsupported DATABASE_URL scheme: {self.database_url}")

        return self._conn

    @contextmanager
    def cursor(self):
        conn = self.connect()
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        finally:
            cur.close()

    def ensure_schema(self) -> None:
        """Create tables if they don't exist."""
        with self.cursor() as cur:
            # Conversation logs table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS conversation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_prompt TEXT NOT NULL,
                    assistant_answer TEXT,
                    tool_calls TEXT,
                    model TEXT,
                    provider TEXT,
                    duration_ms INTEGER,
                    success INTEGER DEFAULT 1,
                    error TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Evaluation checks table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS eval_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    log_id INTEGER NOT NULL,
                    check_name TEXT NOT NULL,
                    passed INTEGER,
                    score REAL,
                    details TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (log_id) REFERENCES conversation_logs(id) ON DELETE CASCADE
                );
            """)

            # Feedback table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    log_id INTEGER NOT NULL,
                    is_good INTEGER NOT NULL,
                    comments TEXT,
                    reference_answer TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (log_id) REFERENCES conversation_logs(id) ON DELETE CASCADE
                );
            """)

    def insert_log(self, log: ConversationLog) -> int:
        """Insert a conversation log and return its ID."""
        with self.cursor() as cur:
            cur.execute(
                """
                INSERT INTO conversation_logs 
                (user_prompt, assistant_answer, tool_calls, model, provider, duration_ms, success, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    log.user_prompt,
                    log.assistant_answer,
                    log.tool_calls,
                    log.model,
                    log.provider,
                    log.duration_ms,
                    1 if log.success else 0,
                    log.error,
                ),
            )
            return cur.lastrowid

    def insert_checks(self, checks: List[CheckResult]) -> None:
        """Insert evaluation checks."""
        with self.cursor() as cur:
            for check in checks:
                cur.execute(
                    """
                    INSERT INTO eval_checks (log_id, check_name, passed, score, details)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        check.log_id,
                        check.check_name.value
                        if hasattr(check.check_name, "value")
                        else check.check_name,
                        1 if check.passed else (0 if check.passed is False else None),
                        check.score,
                        check.details,
                    ),
                )

    def insert_feedback(
        self,
        log_id: int,
        is_good: bool,
        comments: Optional[str] = None,
        reference_answer: Optional[str] = None,
    ) -> int:
        """Insert feedback for a log."""
        with self.cursor() as cur:
            cur.execute(
                """
                INSERT INTO feedback (log_id, is_good, comments, reference_answer)
                VALUES (?, ?, ?, ?)
            """,
                (log_id, 1 if is_good else 0, comments, reference_answer),
            )
            return cur.lastrowid

    def list_logs(
        self,
        limit: int = 100,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> List[dict]:
        """List recent conversation logs."""
        with self.cursor() as cur:
            sql = "SELECT * FROM conversation_logs"
            params = []

            conditions = []
            if provider:
                conditions.append("provider = ?")
                params.append(provider)
            if model:
                conditions.append("model = ?")
                params.append(model)

            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

    def get_log(self, log_id: int) -> Optional[dict]:
        """Get a single log by ID."""
        with self.cursor() as cur:
            cur.execute("SELECT * FROM conversation_logs WHERE id = ?", (log_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_checks(self, log_id: int) -> List[dict]:
        """Get evaluation checks for a log."""
        with self.cursor() as cur:
            cur.execute(
                "SELECT * FROM eval_checks WHERE log_id = ? ORDER BY id", (log_id,)
            )
            return [dict(row) for row in cur.fetchall()]

    def get_feedback(self, log_id: int) -> List[dict]:
        """Get feedback for a log."""
        with self.cursor() as cur:
            cur.execute(
                "SELECT * FROM feedback WHERE log_id = ? ORDER BY created_at DESC",
                (log_id,),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_stats(self) -> dict:
        """Get summary statistics."""
        with self.cursor() as cur:
            # Total conversations
            cur.execute("SELECT COUNT(*) FROM conversation_logs")
            total = cur.fetchone()[0]

            # Successful conversations
            cur.execute("SELECT COUNT(*) FROM conversation_logs WHERE success = 1")
            successful = cur.fetchone()[0]

            # Average duration
            cur.execute(
                "SELECT AVG(duration_ms) FROM conversation_logs WHERE duration_ms IS NOT NULL"
            )
            avg_duration = cur.fetchone()[0] or 0

            # Average eval score
            cur.execute("SELECT AVG(score) FROM eval_checks WHERE score IS NOT NULL")
            avg_score = cur.fetchone()[0] or 0

            # Feedback counts
            cur.execute("SELECT COUNT(*) FROM feedback WHERE is_good = 1")
            positive_feedback = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM feedback WHERE is_good = 0")
            negative_feedback = cur.fetchone()[0]

            return {
                "total_conversations": total,
                "successful_conversations": successful,
                "avg_duration_ms": avg_duration,
                "avg_eval_score": avg_score,
                "positive_feedback": positive_feedback,
                "negative_feedback": negative_feedback,
            }
