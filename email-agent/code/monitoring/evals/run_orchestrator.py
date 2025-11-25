"""Orchestrator for running full evaluation pipeline."""

import subprocess
import sys
from pathlib import Path
from typing import Optional
import pandas as pd


def run_command(cmd: list, description: str) -> bool:
    """
    Run a shell command and report results.

    Args:
        cmd: Command as list of arguments
        description: Description of what's running

    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'=' * 60}")
    print(f"📍 {description}")
    print(f"{'=' * 60}")

    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def run_evaluation_pipeline(
    generate_dataset: bool = True,
    run_agent: bool = True,
    run_judge: bool = True,
    sample_size: Optional[int] = None,
) -> dict:
    """
    Run complete evaluation pipeline.

    Args:
        generate_dataset: Generate ground truth dataset
        run_agent: Run agent on questions
        run_judge: Run judge evaluation
        sample_size: Sample size for judge evaluation

    Returns:
        Dictionary with results paths
    """
    results = {
        "dataset": None,
        "agent_run": None,
        "judge_eval": None,
    }

    # Step 1: Generate dataset
    if generate_dataset:
        success = run_command(
            [
                sys.executable,
                "-m",
                "monitoring.evals.generate_data",
            ],
            "Generating ground truth dataset",
        )
        if not success:
            print("Warning: Dataset generation failed, continuing anyway...")
            results["dataset"] = "monitoring/evals/ground_truth_emails.csv"

    # Step 2: Run agent evaluation
    if run_agent:
        cmd = [sys.executable, "-m", "monitoring.evals.eval_agent_run"]
        success = run_command(
            cmd,
            "Running agent on ground truth questions",
        )
        if not success:
            print("Warning: Agent evaluation failed")
            return results

        # Find latest results file
        reports_dir = Path("monitoring/evals/reports")
        if reports_dir.exists():
            eval_runs = sorted(reports_dir.glob("eval-run-*.csv"), reverse=True)
            if eval_runs:
                results["agent_run"] = str(eval_runs[0])

    # Step 3: Run judge evaluation
    if run_judge:
        cmd = [sys.executable, "-m", "monitoring.evals.eval_agent_judge"]
        if sample_size:
            cmd.extend(["--sample", str(sample_size)])

        success = run_command(
            cmd,
            "Running judge evaluation on agent responses",
        )
        if not success:
            print("Warning: Judge evaluation failed")
        else:
            # Find latest judge results
            reports_dir = Path("monitoring/evals/reports")
            if reports_dir.exists():
                judge_evals = sorted(reports_dir.glob("eval-judge-*.csv"), reverse=True)
                if judge_evals:
                    results["judge_eval"] = str(judge_evals[0])

    return results


def print_final_summary(results: dict):
    """Print final summary of evaluation."""
    print(f"\n{'=' * 60}")
    print("EVALUATION PIPELINE COMPLETE")
    print(f"{'=' * 60}\n")

    if results["dataset"]:
        print(f"Ground Truth Dataset: {results['dataset']}")
        try:
            df = pd.read_csv(results["dataset"])
            print(f"   Total questions: {len(df)}")
            print(f"   Categories: {df['category'].nunique()}")
        except Exception as e:
            print(f"   (Could not read: {e})")

    if results["agent_run"]:
        print(f"\nAgent Run Results: {results['agent_run']}")
        try:
            df = pd.read_csv(results["agent_run"])
            print(f"   Total results: {len(df)}")
            print(f"   Successful: {len(df[df['answer'].notna()])}")
        except Exception as e:
            print(f"   (Could not read: {e})")

    if results["judge_eval"]:
        print(f"\nJudge Evaluation: {results['judge_eval']}")
        try:
            df = pd.read_csv(results["judge_eval"])
            print(f"   Total evaluated: {len(df)}")
            if "overall_score" in df.columns:
                avg_score = df["overall_score"].mean()
                print(f"   Average score: {avg_score:.1f}/100")
                print(f"   Min score: {df['overall_score'].min():.1f}")
                print(f"   Max score: {df['overall_score'].max():.1f}")
        except Exception as e:
            print(f"   (Could not read: {e})")

    print("\nAll results saved to: monitoring/evals/reports/")
    print("=" * 60 + "\n")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run complete email agent evaluation pipeline"
    )
    parser.add_argument(
        "--skip-dataset",
        action="store_true",
        help="Skip dataset generation (use existing)",
    )
    parser.add_argument(
        "--skip-agent",
        action="store_true",
        help="Skip agent evaluation (use existing results)",
    )
    parser.add_argument(
        "--skip-judge",
        action="store_true",
        help="Skip judge evaluation",
    )
    parser.add_argument(
        "--sample",
        type=int,
        help="Sample size for judge evaluation (default: all)",
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("🚀 EMAIL AGENT EVALUATION PIPELINE")
    print("=" * 60)

    results = run_evaluation_pipeline(
        generate_dataset=not args.skip_dataset,
        run_agent=not args.skip_agent,
        run_judge=not args.skip_judge,
        sample_size=args.sample,
    )

    print_final_summary(results)

    return results


if __name__ == "__main__":
    main()
