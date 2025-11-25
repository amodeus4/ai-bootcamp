"""Data models for evaluation system."""

from dataclasses import dataclass, field
from typing import List, Literal
from enum import Enum


class CheckName(str, Enum):
    """Evaluation criteria."""

    ANSWER_RELEVANT = "answer_relevant"
    ANSWER_COMPLETE = "answer_complete"
    ANSWER_ACCURATE = "answer_accurate"
    TOOL_USAGE_CORRECT = "tool_usage_correct"
    TOOL_USAGE_EFFICIENT = "tool_usage_efficient"
    ATTACHMENT_HANDLING = "attachment_handling"
    THREADING_CONTEXT = "threading_context"
    CLARITY = "clarity"


@dataclass
class EvaluationCheck:
    """Result of a single evaluation check."""

    name: CheckName
    passed: bool
    score: int  # 0-10
    reasoning: str


@dataclass
class EvaluationResult:
    """Evaluation result for a single question."""

    question_id: str
    question: str
    agent_response: str
    checks: List[EvaluationCheck]
    overall_score: float  # Percentage 0-100
    notes: str = ""


@dataclass
class TestQuestion:
    """A test question for evaluation."""

    question: str
    summary_answer: str
    difficulty: Literal["beginner", "intermediate", "advanced"]
    intent: Literal["text", "code"]
    relevant_docs: str  # Reference to documentation sections
    filename: str = "agent_readme"


@dataclass
class EvaluationDataset:
    """Collection of test questions."""

    description: str
    questions: List[TestQuestion]
    total_questions: int = field(init=False)

    def __post_init__(self):
        self.total_questions = len(self.questions)
