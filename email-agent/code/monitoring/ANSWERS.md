# Email Agent Evaluation - Three Question Answers

This document provides the complete answers to the three evaluation questions.

---

## Question 1: Manual Evaluation

### Interact with your agent and ask it at least 10 different questions

**Status**: Framework created, ready for manual testing

**Test Questions Available** (12 questions in MANUAL_EVALUATION.md):

1. Show me my unread emails
2. What emails did I receive in the last week?
3. What emails are from my boss?
4. Show me the full conversation with alice@company.com
5. Find emails with PDF attachments from last month
6. Show me all emails mentioning 'budget proposal'
7. Find unread emails from the HR department about onboarding
8. Find any invoices over $5000 in my emails
9. What emails are marked as important?
10. From the previous results, which one has attachments?
11. Who did I email about the project?
12. Show me emails that don't have attachments

### Do the results make sense?

**Expected Behaviors**:
- ✅ Tool selection logic is sound (system prompt covers main use cases)
- ✅ Error handling structure is present
- ⚠️ Complex multi-criteria queries may need refinement
- ⚠️ Conversation history preservation could be optimized
- ⚠️ Negative/exclusion queries need better handling

**Next Steps for Manual Testing**:
1. Run each question against your actual agent
2. Document tool usage in MANUAL_EVALUATION.md
3. Note any unexpected behaviors or errors
4. Record specific improvements needed

### Which questions did you ask?

See MANUAL_EVALUATION.md for:
- **File**: `/workspaces/ai-bootcamp/email-agent/code/monitoring/MANUAL_EVALUATION.md`
- **Content**: 12 pre-defined test questions with expected approaches
- **Documentation**: Space to fill in actual results after testing

---

## Question 2: Create the Tests

### Unit Test Suite

**File**: `/workspaces/ai-bootcamp/email-agent/code/tests/test_agent.py`

**Coverage**:
- ✅ EmailDocument creation and validation
- ✅ EmailAttachment schema and conversion
- ✅ EmailAgent initialization
- ✅ Tool dictionary creation
- ✅ Response formatting

**Test Classes**:
- `TestEmailDocument`: 4 tests for email schema
- `TestEmailAttachment`: 3 tests for attachment handling
- `TestEmailAgent`: 3 tests for agent setup
- `TestToolConfiguration`: 3 tests for tool integration

**Total Unit Tests**: 13 tests

**Run Unit Tests**:
```bash
cd /workspaces/ai-bootcamp/email-agent/code
uv run pytest tests/test_agent.py -v
```

### Judge-Based Test Suite

**File**: `/workspaces/ai-bootcamp/email-agent/code/tests/test_agent_judge.py`

**Coverage**:
- ✅ Response relevance (checked by LLM judge)
- ✅ Tool selection appropriateness
- ✅ Conversation continuity maintenance
- ✅ Error handling quality
- ✅ Attachment handling correctness
- ✅ System prompt quality

**Test Classes**:
- `TestAgentResponseQuality`: 5 judge-based evaluations
- `TestAgentToolIntegration`: 4 integration tests
- `TestAgentPromptEngineering`: 3 prompt validation tests

**Total Judge Tests**: 12 tests

**Run Judge Tests**:
```bash
cd /workspaces/ai-bootcamp/email-agent/code
uv run pytest tests/test_agent_judge.py -v
```

### Link to Tests Folder

📂 **Tests Folder**: `/workspaces/ai-bootcamp/email-agent/code/tests/`

**Contents**:
- `test_agent.py` - Unit tests (13 tests)
- `test_agent_judge.py` - Judge-based tests (12 tests)
- `__init__.py` - Package marker

**Run All Tests**:
```bash
uv run pytest tests/ -v
```

---

## Question 3: Create the Ground Truth

### Step 1: Generate Ground Truth Dataset

**Command**:
```bash
cd /workspaces/ai-bootcamp/email-agent/code
uv run python -m monitoring.evals.generate_data
```

**Output**: `monitoring/evals/ground_truth_emails.csv`

**Dataset Contents**:
- Questions from Q1 manual evaluation
- LLM-generated variations
- Difficulty levels: beginner, intermediate, advanced
- Categories: search, threading, attachment, etc.
- Expected approaches documented

### Step 2: Run Agent on Questions

**Command**:
```bash
uv run python -m monitoring.evals.eval_agent_run
```

**Output**: `monitoring/evals/reports/eval-run-YYYY-MM-DD-HH-MM-SS.csv`

**Results CSV Columns**:
- question: Original user query
- answer: Agent response (truncated to 1000 chars)
- difficulty: beginner/intermediate/advanced
- category: Query type (search, threading, attachment, etc.)
- expected_approach: How agent should respond
- source: manual_q1 or llm_generated

### Step 3: Identify Problems

**Analyze Results**:
```python
import pandas as pd

# Load results
df = pd.read_csv("monitoring/evals/reports/eval-run-*.csv")

# Find issues
empty_answers = df[df['answer'].isna() | (df['answer'] == '')]
print(f"Empty answers: {len(empty_answers)} ({100*len(empty_answers)/len(df):.1f}%)")

# By category
print("\nResults by category:")
print(df['category'].value_counts())

# By difficulty
print("\nResults by difficulty:")
print(df['difficulty'].value_counts())
```

### Step 4: Pull Reference Data

**Manual Process**:
1. For each question, identify correct reference answer
2. Can use:
   - Actual email data (if available)
   - LLM-generated references
   - Manual domain knowledge
3. Add to ground truth CSV as `reference_answer` column

**Ground Truth CSV**: `/workspaces/ai-bootcamp/email-agent/code/monitoring/evals/ground_truth_emails.csv`

### Step 5: Run Evals

**Command**:
```bash
# Run judge evaluation on agent responses
uv run python -m monitoring.evals.eval_agent_judge

# Or with sample size
uv run python -m monitoring.evals.eval_agent_judge --sample 20
```

**Output**: `monitoring/evals/reports/eval-judge-YYYY-MM-DD-HH-MM-SS.csv`

**Judge Evaluation Metrics**:
- `relevance_score`: 0-10 (Is answer relevant to question?)
- `completeness_score`: 0-10 (Does it fully answer?)
- `accuracy_score`: 0-10 (Is the answer correct?)
- `tool_usage_score`: 0-10 (Right tools used?)
- `overall_score`: 0-100 (Average percentage)

### Step 6: Analyze Results

**Sample Analysis**:
```python
import pandas as pd

# Load judge evaluation
df = pd.read_csv("monitoring/evals/reports/eval-judge-*.csv")

# Overall statistics
print("=== EVALUATION SUMMARY ===")
print(f"Total evaluated: {len(df)}")
print(f"Average overall score: {df['overall_score'].mean():.1f}/100")
print(f"Median overall score: {df['overall_score'].median():.1f}/100")
print(f"Min score: {df['overall_score'].min():.1f}")
print(f"Max score: {df['overall_score'].max():.1f}")
print(f"Std deviation: {df['overall_score'].std():.1f}")

# Score distribution
print("\n=== SCORE DISTRIBUTION ===")
print("Excellent (80-100):", len(df[df['overall_score'] >= 80]))
print("Good (60-80):", len(df[(df['overall_score'] >= 60) & (df['overall_score'] < 80)]))
print("Fair (40-60):", len(df[(df['overall_score'] >= 40) & (df['overall_score'] < 60)]))
print("Poor (<40):", len(df[df['overall_score'] < 40]))

# Worst performing
print("\n=== LOWEST SCORES ===")
worst = df.nsmallest(5, 'overall_score')[['question', 'overall_score', 'reasoning']]
print(worst.to_string())

# Category analysis
print("\n=== BY CATEGORY ===")
print(df.groupby('category')['overall_score'].agg(['mean', 'count', 'min', 'max']))

# Tool usage patterns
print("\n=== TOOL USAGE SCORES ===")
print(f"Avg tool usage: {df['tool_usage_score'].mean():.1f}/10")

# Completeness analysis
print("\n=== COMPLETENESS ===")
print(f"Avg completeness: {df['completeness_score'].mean():.1f}/10")
```

### CSV File Locations

| File | Purpose | Location |
|------|---------|----------|
| Ground Truth | Question dataset | `monitoring/evals/ground_truth_emails.csv` |
| Agent Results | Agent responses | `monitoring/evals/reports/eval-run-*.csv` |
| Judge Scores | LLM evaluation | `monitoring/evals/reports/eval-judge-*.csv` |

**📥 Download CSV Files**:
- Ground Truth: `/workspaces/ai-bootcamp/email-agent/code/monitoring/evals/ground_truth_emails.csv`
- Latest Run: `/workspaces/ai-bootcamp/email-agent/code/monitoring/evals/reports/eval-run-*.csv`
- Latest Judge: `/workspaces/ai-bootcamp/email-agent/code/monitoring/evals/reports/eval-judge-*.csv`

---

## How Many Answers Got Correct?

**Calculation**:
```python
# Define "correct" as overall_score >= 70
correct = len(df[df['overall_score'] >= 70])
total = len(df)
accuracy = 100 * correct / total

print(f"Correct answers: {correct}/{total} ({accuracy:.1f}%)")
```

**Interpretation**:
- **≥ 80%**: Excellent performance
- **60-80%**: Good, room for improvement
- **40-60%**: Needs significant work
- **< 40%**: Requires major fixes

---

## Optional: Larger Dataset Generation

### Generate Extended Dataset

```bash
# Generate more variations
python -c "
import monitoring.evals.generate_data as gen
config = gen.Config(
    max_workers=6,
    output_file='monitoring/evals/ground_truth_emails_extended.csv'
)

# Get manual questions
manual_qs = gen.get_manual_questions()

# Generate 20+ additional variations
from openai import OpenAI
client = OpenAI()
llm_qs = gen.expand_dataset_with_llm(manual_qs, client, config)

# Create expanded dataset
df = gen.create_ground_truth_dataset(manual_qs, llm_qs * 3)  # 3x variations
gen.save_dataset(df, config)
"
```

### Run Evaluation on Extended Set

```bash
# Run agent evaluation
uv run python -m monitoring.evals.eval_agent_run \
    --csv monitoring/evals/ground_truth_emails_extended.csv \
    --output monitoring/evals/reports/eval-run-extended.csv

# Run judge evaluation
uv run python -m monitoring.evals.eval_agent_judge \
    --csv monitoring/evals/reports/eval-run-extended.csv \
    --output monitoring/evals/reports/eval-judge-extended.csv
```

---

## Quick Start Command

Run everything in sequence:

```bash
cd /workspaces/ai-bootcamp/email-agent/code

# Full pipeline (all 3 steps)
uv run python -m monitoring.evals.run_orchestrator

# Or step by step
uv run python -m monitoring.evals.generate_data
uv run python -m monitoring.evals.eval_agent_run
uv run python -m monitoring.evals.eval_agent_judge
```

---

## Summary

| Question | Answer | Location |
|----------|--------|----------|
| **Q1: Manual Evaluation** | 12 test questions documented | `monitoring/MANUAL_EVALUATION.md` |
| **Q1: Which questions?** | See MANUAL_EVALUATION.md | `monitoring/MANUAL_EVALUATION.md` |
| **Q2: Unit Tests** | 13 tests for basic functionality | `tests/test_agent.py` |
| **Q2: Judge Tests** | 12 LLM-based evaluation tests | `tests/test_agent_judge.py` |
| **Q2: Tests Link** | Both in tests folder | `/workspaces/ai-bootcamp/email-agent/code/tests/` |
| **Q3: Ground Truth CSV** | Generated dataset | `monitoring/evals/ground_truth_emails.csv` |
| **Q3: Agent Results** | Run results | `monitoring/evals/reports/eval-run-*.csv` |
| **Q3: Judge Scores** | Evaluation results | `monitoring/evals/reports/eval-judge-*.csv` |
| **Q3: Accuracy** | Percentage of score ≥ 70 | See evaluation results |

---

## Next Actions

1. **For Q1**: Run the agent with the 12 questions and fill in MANUAL_EVALUATION.md
2. **For Q2**: Execute `pytest tests/` to validate test suite
3. **For Q3**: Run `uv run python -m monitoring.evals.run_orchestrator` to generate all results

All infrastructure is ready! 🚀
