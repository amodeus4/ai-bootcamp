"""Generate evaluation dataset from manual questions and LLM."""

import json
from pathlib import Path
from typing import List
from dataclasses import dataclass

import pandas as pd
from openai import OpenAI
from pydantic import BaseModel, Field


@dataclass
class Config:
    """Configuration for dataset generation."""

    model: str = "gpt-4o-mini"
    output_file: str = "monitoring/evals/ground_truth_emails.csv"


class Question(BaseModel):
    """A test question for evaluation."""

    question: str = Field(..., description="The user query to evaluate")
    expected_approach: str = Field(
        ..., description="How the agent should approach answering this"
    )
    difficulty: str = Field(..., description="beginner/intermediate/advanced")
    category: str = Field(
        ..., description="Type of query: search, thread, attachment, etc"
    )


class GeneratedDataset(BaseModel):
    """Generated evaluation questions."""

    questions: List[Question] = Field(..., description="List of test questions")


def get_manual_questions() -> List[dict]:
    """Get manual questions from Q1 evaluation."""
    # These will be the 10+ questions you interact with manually
    manual_questions = [
        {
            "question": "Show me emails from the last 7 days",
            "expected_approach": "Use elasticsearch_search with date_from parameter",
            "difficulty": "beginner",
            "category": "date-based search",
            "source": "manual_q1",
        },
        {
            "question": "What emails from my boss are unread?",
            "expected_approach": "Use elasticsearch_search with sender filter and search_text",
            "difficulty": "beginner",
            "category": "sender + status search",
            "source": "manual_q1",
        },
        {
            "question": "Find all conversation with john@company.com",
            "expected_approach": "Use conversation_history tool for complete thread",
            "difficulty": "intermediate",
            "category": "conversation threading",
            "source": "manual_q1",
        },
        {
            "question": "Show me emails with invoices",
            "expected_approach": "Use search_attachments for PDF/document content",
            "difficulty": "intermediate",
            "category": "attachment search",
            "source": "manual_q1",
        },
        {
            "question": "What emails mention budget?",
            "expected_approach": "Use elasticsearch_search with keyword",
            "difficulty": "beginner",
            "category": "keyword search",
            "source": "manual_q1",
        },
    ]
    return manual_questions


def expand_dataset_with_llm(
    base_questions: List[dict], client: OpenAI, config: Config
) -> List[dict]:
    """
    Expand manual questions with LLM-generated variations.
    Generates multiple batches to get 100+ questions.

    Args:
        base_questions: Manual questions from Q1
        client: OpenAI client
        config: Configuration

    Returns:
        Expanded list of questions
    """
    all_generated = []

    # Generate multiple batches of variations
    # Each batch generates 30-50 questions
    num_batches = 5

    for batch_num in range(num_batches):
        print(f"   Batch {batch_num + 1}/{num_batches}...")

        prompt = f"""
Given these email agent use cases, generate 40 diverse and realistic user questions that test the agent's capabilities.

Base use cases:
{json.dumps(base_questions, indent=2)}

Generate 40 variations that:
1. Mix difficulty levels: 60% beginner, 30% intermediate, 10% advanced
2. Test different capabilities: search, filtering, threading, attachments, combinations
3. Are realistic questions a busy professional would ask
4. Cover edge cases and complex scenarios
5. Batch {batch_num + 1}: Focus on different angles than previous batches

For each question, provide a JSON object with:
- question: the user query (string) - natural language, not technical
- expected_approach: how agent should handle it (string) - which tools to use
- difficulty: beginner/intermediate/advanced (string)
- category: type of query (string) - e.g., "date search", "sender filter", "complex query"

Return a JSON array of exactly 40 question objects.
""".strip()

        try:
            response = client.chat.completions.create(
                model=config.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0.8,  # Higher for more diversity
            )

            # Parse the response
            content = response.choices[0].message.content

            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            parsed_data = json.loads(content)

            # Ensure we have a list
            if not isinstance(parsed_data, list):
                parsed_data = [parsed_data]

            generated_questions = [
                {
                    "question": q.get("question", ""),
                    "expected_approach": q.get("expected_approach", ""),
                    "difficulty": q.get("difficulty", "intermediate"),
                    "category": q.get("category", "general"),
                    "source": "llm_generated",
                }
                for q in parsed_data
                if q.get("question")  # Only include if has question
            ]

            all_generated.extend(generated_questions)
            print(f"      Added {len(generated_questions)} questions")

        except Exception as e:
            print(f"      Warning: Batch {batch_num + 1} error: {e}")

    return all_generated


def create_ground_truth_dataset(
    manual_questions: List[dict], llm_expanded: List[dict]
) -> pd.DataFrame:
    """Create ground truth dataset from manual and LLM questions."""
    all_questions = manual_questions + llm_expanded

    # Remove duplicates
    seen = set()
    unique_questions = []
    for q in all_questions:
        question_text = q["question"].lower().strip()
        if question_text not in seen:
            seen.add(question_text)
            unique_questions.append(q)

    df = pd.DataFrame(unique_questions)
    return df


def save_dataset(df: pd.DataFrame, config: Config):
    """Save dataset to CSV."""
    output_path = Path(config.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index=False)
    print(f"✅ Saved {len(df)} questions to {output_path}")
    print("\nDataset distribution:")
    print(df["difficulty"].value_counts().sort_index().to_string())
    print("\nCategory distribution:")
    print(df["category"].value_counts().head(10).to_string())

    return output_path


def main(config: Config):
    """Main data generation pipeline."""
    print("📊 Generating evaluation dataset...\n")

    print("1️⃣  Loading manual questions from Q1...")
    manual_questions = get_manual_questions()
    print(f"   Loaded {len(manual_questions)} manual questions\n")

    print("2️⃣  Expanding dataset with LLM...")
    client = OpenAI()
    llm_expanded = expand_dataset_with_llm(manual_questions, client, config)
    print(f"   Generated {len(llm_expanded)} additional questions\n")

    print("3️⃣  Creating ground truth dataset...")
    df = create_ground_truth_dataset(manual_questions, llm_expanded)
    print(f"   Total unique questions: {len(df)}\n")

    print("4️⃣  Saving dataset...")
    output_path = save_dataset(df, config)

    return output_path


if __name__ == "__main__":
    config = Config()
    main(config)
