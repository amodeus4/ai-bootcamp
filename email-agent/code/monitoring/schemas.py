"""Monitoring schemas for email agent."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime


class CheckName(str, Enum):
    """Evaluation check names."""

    response_not_empty = "response_not_empty"
    tool_called = "tool_called"
    response_relevant = "response_relevant"
    no_error = "no_error"
    correct_tool_selection = "correct_tool_selection"
    answer_complete = "answer_complete"


@dataclass
class ConversationLog:
    """Log record for a conversation turn."""

    user_prompt: str
    assistant_answer: str
    tool_calls: Optional[str] = None  # JSON string of tool calls
    model: Optional[str] = None
    provider: Optional[str] = None
    duration_ms: Optional[int] = None
    success: bool = True
    error: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class CheckResult:
    """Result of an evaluation check."""

    log_id: int
    check_name: CheckName
    passed: Optional[bool] = None
    score: Optional[float] = None
    details: Optional[str] = None


@dataclass
class Feedback:
    """User feedback on a response."""

    log_id: int
    is_good: bool
    comments: Optional[str] = None
    reference_answer: Optional[str] = None
