"""Run agent on evaluation questions and collect results."""

import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List
import pandas as pd
import sys
from dotenv import load_dotenv

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from email_agent import (
    EmailAgent,
    authenticate_gmail,
    ElasticsearchEmailStore,
    GmailFetchTool,
    ElasticsearchSearchTool,
    ElasticsearchWriteTool,
    ConversationHistoryTool,
    SearchAttachmentsTool,
)


_gmail_service = None
_es_store = None


def initialize_dependencies():
    """Initialize shared dependencies (Gmail and Elasticsearch)."""
    global _gmail_service, _es_store

    if _gmail_service is not None and _es_store is not None:
        return _gmail_service, _es_store

    load_dotenv()

    # Configuration
    es_host = os.getenv("ES_HOST", "localhost")
    es_port = int(os.getenv("ES_PORT", "9200"))
    es_index = os.getenv("ES_INDEX_NAME", "emails")
    credentials_file = os.getenv("CREDENTIALS_FILE", "credentials.json")

    try:
        _gmail_service = authenticate_gmail(credentials_file)

        _es_store = ElasticsearchEmailStore(
            es_host=es_host, es_port=es_port, index_name=es_index
        )

        return _gmail_service, _es_store
    except Exception as e:
        print(f"Failed to initialize dependencies: {e}")
        raise


def create_fresh_agent(gmail_service, es_store):
    """Create a fresh agent instance with new conversation history."""
    try:
        # Create fresh tools for this agent
        gmail_tool = GmailFetchTool(gmail_service)
        search_tool = ElasticsearchSearchTool(es_store)
        write_tool = ElasticsearchWriteTool(es_store)
        conversation_tool = ConversationHistoryTool(es_store)
        attachment_tool = SearchAttachmentsTool(es_store)

        agent = EmailAgent(
            tools=[
                gmail_tool,
                search_tool,
                write_tool,
                conversation_tool,
                attachment_tool,
            ]
        )

        return agent
    except Exception as e:
        print(f" Failed to create agent: {e}")
        raise


def load_ground_truth(
    csv_path: str = "monitoring/evals/ground_truth_emails.csv",
) -> List[dict]:
    """Load ground truth data from CSV file.

    Args:
        csv_path: Path to the ground truth CSV file

    Returns:
        List of ground truth records as dictionaries
    """
    df_ground_truth = pd.read_csv(csv_path)
    return df_ground_truth.to_dict(orient="records")


def run_agent_on_question(question_record: dict, gmail_service, es_store):
    """
    Run the agent on a single question with a fresh agent instance.

    Args:
        question_record: Dictionary containing the question
        gmail_service: Gmail service instance
        es_store: Elasticsearch store instance

    Returns:
        Tuple of (question_record, result) or (None, None) on error
    """
    try:
        # Create a fresh agent for this question to avoid context length issues
        agent = create_fresh_agent(gmail_service, es_store)

        # Run the agent with the question
        result = agent.chat(question_record["question"])

        return (question_record, result)
    except Exception as e:
        print(f"Error processing {question_record}: {e}")
        traceback.print_exc()
        return (None, None)


def run_evaluation(
    ground_truth: List[dict], gmail_service, es_store, max_concurrent: int = 5
) -> List[Tuple]:
    """
    Run evaluation on all ground truth questions.

    Args:
        ground_truth: List of ground truth records
        gmail_service: Gmail service instance
        es_store: Elasticsearch store instance
        max_concurrent: Maximum concurrent agent runs

    Returns:
        List of (question, result) tuples
    """
    all_results = []

    for i, q in enumerate(ground_truth, 1):
        print(f"Processing question {i}/{len(ground_truth)}: {q['question'][:50]}...")
        result = run_agent_on_question(q, gmail_service, es_store)
        all_results.append(result)

    return all_results


def prepare_results_for_analysis(all_results: List[Tuple]) -> List[dict]:
    """
    Prepare evaluation results for analysis.

    Args:
        all_results: List of (question, result) tuples

    Returns:
        List of row dictionaries containing questions and answers
    """
    rows = []

    for q, r in all_results:
        if q is None or r is None:
            continue

        row = {
            "question": q["question"],
            "answer": r if isinstance(r, str) else str(r)[:1000],
            "difficulty": q.get("difficulty", "unknown"),
            "category": q.get("category", "unknown"),
            "expected_approach": q.get("expected_approach", ""),
            "source": q.get("source", "unknown"),
        }
        rows.append(row)

    return rows


def save_results(rows: List[dict], output_path: Optional[str] = None) -> str:
    """
    Save evaluation results to CSV file.

    Args:
        rows: List of result dictionaries
        output_path: Path to save file (None = auto-generate)

    Returns:
        Path to the saved file
    """
    if output_path is None:
        # Create reports directory if it doesn't exist
        reports_dir = Path("monitoring/evals/reports")
        reports_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        output_path = f"monitoring/evals/reports/eval-run-{timestamp}.csv"

    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)

    print(f"\n Results saved to {output_path}")
    print(f"   Total results: {len(df)}")

    return output_path


def run_agent_evaluation(
    csv_path: str = "monitoring/evals/ground_truth_emails.csv",
    output_path: Optional[str] = None,
) -> Tuple[str, pd.DataFrame]:
    """
    Run complete agent evaluation pipeline.

    Args:
        csv_path: Path to ground truth CSV
        output_path: Output file path

    Returns:
        Tuple of (output_path, results_df)
    """
    # Initialize dependencies
    print("Initializing dependencies...\n")
    gmail_service, es_store = initialize_dependencies()
    print("Dependencies initialized\n")

    # Load ground truth
    print(f"📥 Loading ground truth from {csv_path}...")
    ground_truth = load_ground_truth(csv_path=csv_path)
    print(f"   Loaded {len(ground_truth)} ground truth questions\n")

    # Run evaluation
    print("🤖 Running agent evaluation...\n")
    all_results = run_evaluation(ground_truth, gmail_service, es_store)

    valid_results = [(q, r) for q, r in all_results if q is not None and r is not None]
    print(f"\n Successful results: {len(valid_results)}/{len(all_results)}")

    # Prepare results
    rows = prepare_results_for_analysis(all_results)
    df_run = pd.DataFrame(rows)

    # Save results
    saved_path = save_results(rows, output_path)

    return saved_path, df_run


def main_cli():
    """Command-line interface for running agent evaluation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run agent evaluation on ground truth dataset"
    )
    parser.add_argument(
        "--csv",
        default="monitoring/evals/ground_truth_emails.csv",
        help="Path to ground truth CSV file",
    )
    parser.add_argument(
        "--output", help="Output path for results (auto-generated if not specified)"
    )

    args = parser.parse_args()

    saved_path, df_run = run_agent_evaluation(
        csv_path=args.csv,
        output_path=args.output,
    )

    print("\n=== Evaluation Summary ===")
    print(f"Total questions: {len(df_run)}")
    print(f"Results saved: {saved_path}")


if __name__ == "__main__":
    main_cli()
