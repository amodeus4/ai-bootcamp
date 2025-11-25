"""Judge-based evaluation of agent responses."""

import json
from pathlib import Path
from typing import List, Tuple
import pandas as pd
from openai import OpenAI
from pydantic import BaseModel, Field


class EvaluationScore(BaseModel):
    """Evaluation score for a single response."""

    question: str = Field(..., description="The original question")
    answer: str = Field(..., description="Agent's answer (truncated)")
    relevance_score: int = Field(
        ..., description="How relevant is the answer (0-10)", ge=0, le=10
    )
    completeness_score: int = Field(
        ..., description="How complete is the answer (0-10)", ge=0, le=10
    )
    accuracy_score: int = Field(
        ..., description="How accurate is the answer (0-10)", ge=0, le=10
    )
    tool_usage_score: int = Field(
        ..., description="Did agent use right tools (0-10)", ge=0, le=10
    )
    overall_score: float = Field(..., description="Overall score as percentage (0-100)")
    reasoning: str = Field(..., description="Explanation of scores")
    suggestions: str = Field(..., description="Suggestions for improvement")


class EvaluationResults(BaseModel):
    """Collection of evaluation scores."""

    scores: List[EvaluationScore] = Field(..., description="List of evaluation scores")


def load_run_results(csv_path: str) -> pd.DataFrame:
    """Load previous run results."""
    df = pd.read_csv(csv_path)
    return df


def get_judge_instructions() -> str:
    """Get system instructions for the judge."""
    return """
You are an expert evaluator for an email management agent powered by OpenAI and Elasticsearch.

Your task is to evaluate the agent's responses to user questions about their emails.

For each question-answer pair, evaluate on these criteria:
1. **Relevance (0-10)**: Is the answer relevant to the question asked?
2. **Completeness (0-10)**: Does the answer fully address the question? Are there missing details?
3. **Accuracy (0-10)**: Is the answer factually correct about what the agent should do?
4. **Tool Usage (0-10)**: Did the agent use the appropriate tools for the task?

Based on these scores, calculate an overall score (0-100) as their average.

Provide reasoning for your scores and suggestions for improvement.

Note: You're evaluating whether the agent's response makes sense conceptually, not whether the actual email data is correct (since this is a test environment).
""".strip()


def evaluate_responses(
    df_results: pd.DataFrame, model: str = "gpt-4o-mini", sample_size: int = None
) -> pd.DataFrame:
    """
    Evaluate agent responses using judge LLM.

    Args:
        df_results: DataFrame with columns: question, answer, difficulty, category, etc
        model: OpenAI model to use
        sample_size: Number of responses to evaluate (None = all)

    Returns:
        DataFrame with evaluation scores
    """
    client = OpenAI()
    instructions = get_judge_instructions()

    # Sample if needed
    df_to_eval = df_results.head(sample_size) if sample_size else df_results

    evaluation_scores = []

    for idx, row in df_to_eval.iterrows():
        print(f"Evaluating {idx + 1}/{len(df_to_eval)}: {row['question'][:40]}...")

        question = row["question"]
        answer = str(row["answer"])[:1000]  # Truncate long answers

        eval_prompt = f"""
Evaluate this email agent response on a scale of 0-10 for each dimension:

Question: {question}
Answer: {answer}

Provide a JSON response with these fields:
- relevance_score (0-10): Is the answer relevant to the question?
- completeness_score (0-10): Does it fully answer the question?
- accuracy_score (0-10): Is the information accurate?
- tool_usage_score (0-10): Did the agent use appropriate tools?
- overall_score (0-100): Average of the above scores
- reasoning (string): Explanation of the scores
- suggestions (string): How to improve the response

Return valid JSON only.
""".strip()

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": eval_prompt},
                ],
                temperature=0.5,
            )

            # Extract the response
            content = response.choices[0].message.content

            # Extract JSON from response (it might be wrapped in markdown code blocks)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            score_dict = json.loads(content)

            score_dict["question"] = question
            score_dict["answer"] = answer
            evaluation_scores.append(score_dict)

        except Exception as e:
            print(f"  Warning: Error evaluating: {e}")
            evaluation_scores.append(
                {
                    "question": question,
                    "answer": answer,
                    "relevance_score": 5,
                    "completeness_score": 5,
                    "accuracy_score": 5,
                    "tool_usage_score": 5,
                    "overall_score": 50,
                    "reasoning": f"Evaluation attempted but encountered: {str(e)[:100]}",
                    "suggestions": "Manual review recommended",
                }
            )

    df_scores = pd.DataFrame(evaluation_scores)
    return df_scores


def save_evaluation_results(df_scores: pd.DataFrame, output_path: str = None) -> str:
    """Save evaluation results to CSV."""
    if output_path is None:
        reports_dir = Path("monitoring/evals/reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        output_path = f"monitoring/evals/reports/eval-judge-{timestamp}.csv"

    df_scores.to_csv(output_path, index=False)
    print(f"\n Judge evaluation saved to {output_path}")
    return output_path


def print_evaluation_summary(df_scores: pd.DataFrame):
    """Print summary of evaluation results."""
    print("\n=== Judge Evaluation Summary ===")
    print(f"Total evaluated: {len(df_scores)}")
    print(f"Average overall score: {df_scores['overall_score'].mean():.1f}/100")
    print(f"Average relevance: {df_scores['relevance_score'].mean():.1f}/10")
    print(f"Average completeness: {df_scores['completeness_score'].mean():.1f}/10")
    print(f"Average accuracy: {df_scores['accuracy_score'].mean():.1f}/10")
    print(f"Average tool usage: {df_scores['tool_usage_score'].mean():.1f}/10")

    # correct responses
    correct = len(df_scores[df_scores["overall_score"] >= 70])
    total = len(df_scores)
    percentage = (correct / total * 100) if total > 0 else 0
    print(f"\nCorrect (>= 70/100): {correct}/{total} ({percentage:.1f}%)")

    # Show distribution
    print("\nScore distribution (overall):")
    bins = [0, 20, 40, 60, 80, 100]
    df_scores["score_bin"] = pd.cut(df_scores["overall_score"], bins=bins)
    print(df_scores["score_bin"].value_counts().sort_index().to_string())


def run_judge_evaluation(
    csv_path: str = "monitoring/evals/reports/eval-run-*.csv",
    sample_size: int = None,
    output_path: str = None,
) -> Tuple[str, pd.DataFrame]:
    """
    Run judge evaluation on agent results.

    Args:
        csv_path: Path to agent run results CSV
        sample_size: Number of results to evaluate
        output_path: Output file path

    Returns:
        Tuple of (output_path, results_df)
    """
    # Find latest eval run if wildcard
    if "*" in csv_path:
        reports_dir = Path("monitoring/evals/reports")
        eval_runs = sorted(reports_dir.glob("eval-run-*.csv"), reverse=True)
        if not eval_runs:
            print("❌ No evaluation run results found")
            return None, None
        csv_path = str(eval_runs[0])
        print(f"Using latest run: {csv_path}\n")

    print(f"📥 Loading run results from {csv_path}...")
    df_results = load_run_results(csv_path)
    print(f"   Loaded {len(df_results)} results\n")

    print("🏆 Running judge evaluation...\n")
    df_scores = evaluate_responses(df_results, sample_size=sample_size)

    # Save results
    saved_path = save_evaluation_results(df_scores, output_path)

    # Print summary
    print_evaluation_summary(df_scores)

    return saved_path, df_scores


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run judge evaluation on agent results"
    )
    parser.add_argument(
        "--csv",
        default="monitoring/evals/reports/eval-run-*.csv",
        help="Path to eval run results CSV (supports wildcards)",
    )
    parser.add_argument(
        "--sample", type=int, help="Sample size for evaluation (default: all)"
    )
    parser.add_argument("--output", help="Output path for results")

    args = parser.parse_args()

    run_judge_evaluation(
        csv_path=args.csv,
        sample_size=args.sample,
        output_path=args.output,
    )
