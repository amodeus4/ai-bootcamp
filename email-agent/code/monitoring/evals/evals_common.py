"""Common utilities for evaluation."""

from pathlib import Path
from typing import List, Dict, Tuple


def simplify_messages(messages: List[Dict]) -> List[Dict]:
    """Simplify messages for storage (remove tool_calls details)."""
    simplified = []
    for msg in messages:
        if isinstance(msg, dict):
            simple_msg = {
                "role": msg.get("role", ""),
                "content": msg.get("content", "")[:500] if msg.get("content") else "",
            }
            simplified.append(simple_msg)
    return simplified


def calculate_cost(model: str, results: List[Tuple]) -> Dict[str, float]:
    """
    Calculate evaluation cost.

    Args:
        model: Model name
        results: List of (question, result) tuples

    Returns:
        Dictionary with cost information
    """
    # Simple cost estimation - can be expanded with actual pricing
    cost_per_call = 0.01  # Placeholder
    total_calls = len([r for r in results if r[1] is not None])
    total_cost = total_calls * cost_per_call

    return {
        "total_calls": total_calls,
        "cost_per_call": cost_per_call,
        "total_cost": total_cost,
    }


def ensure_reports_dir() -> Path:
    """Ensure reports directory exists."""
    reports_dir = Path("monitoring/evals/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir
