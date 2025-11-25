# Email Agent Evaluation System

This document provides a complete guide to the three-question evaluation framework for the email agent project.

## Overview

The evaluation system follows the week3 code structure and addresses three key questions:

1. **Manual Evaluation (Q1)**: Interactive testing and observations
2. **Test Suites (Q2)**: Unit tests and judge-based evaluations
3. **Ground Truth Dataset (Q3)**: Dataset creation, agent runs, and evaluation metrics

## Question 1: Manual Evaluation

### What to Do

Interact with your agent and ask it at least 10 different questions based on your use case. Observe whether the results make sense.

### Where

- **Documentation**: `/workspaces/ai-bootcamp/email-agent/code/monitoring/MANUAL_EVALUATION.md`
- **Questions Template**: 12 pre-defined questions covering different scenarios

### Test Scenarios

The manual evaluation template includes 12 test questions covering:

- ✅ Basic unread email queries
- ✅ Date-range searches
- ✅ Sender-based filtering
- ✅ Conversation threading
- ✅ Attachment searches
- ✅ Keyword searches
- ✅ Multi-criteria queries
- ✅ Content-in-attachments search
- ✅ Category/label filtering
- ✅ Multi-turn conversation
- ✅ Recipient-based queries
- ✅ Edge cases and negation

### How to Run

1. Start the agent:
```bash
cd /workspaces/ai-bootcamp/email-agent/code
make run
```

2. Type the questions from `MANUAL_EVALUATION.md` one by one

3. Document observations in the markdown file:
   - Does the result make sense?
   - Did it use the right tools?
   - Any errors or unexpected behavior?

4. Record issues found for reference in Q2/Q3

## Question 2: Create Test Suites

### What to Do

Based on Q1 interactions, create two test suites:

1. **Unit Tests**: Simple checks (references present, schemas valid, etc.)
2. **Judge Tests**: Use LLM judge to evaluate complex response quality

### Where

- **Unit Tests**: `/workspaces/ai-bootcamp/email-agent/code/tests/test_agent.py`
- **Judge Tests**: `/workspaces/ai-bootcamp/email-agent/code/tests/test_agent_judge.py`

### Test Coverage

#### Unit Tests (test_agent.py)
- Email document creation and validation
- Attachment metadata handling
- Agent initialization
- Tool configuration
- Response formatting

#### Judge-Based Tests (test_agent_judge.py)
- Response relevance evaluation
- Tool selection appropriateness
- Conversation continuity
- Error handling quality
- Attachment handling correctness
- System prompt quality

### How to Run

Run all unit tests:
```bash
cd /workspaces/ai-bootcamp/email-agent/code
uv run pytest tests/test_agent.py -v
```

Run judge-based tests (skipped by default):
```bash
uv run pytest tests/test_agent_judge.py -v
```

Run with coverage:
```bash
uv run pytest tests/ --cov=email_agent --cov-report=html
```

## Question 3: Create Ground Truth Dataset

### What to Do

1. Generate ground truth dataset from Q1 questions
2. Run agent on all questions
3. Create CSV with results
4. Identify where agent performs well/poorly
5. Run evals and measure accuracy

### Where

- **Ground Truth CSV**: `/workspaces/ai-bootcamp/email-agent/code/monitoring/evals/ground_truth_emails.csv`
- **Agent Run Results**: `/workspaces/ai-bootcamp/email-agent/code/monitoring/evals/reports/eval-run-*.csv`
- **Judge Evaluation**: `/workspaces/ai-bootcamp/email-agent/code/monitoring/evals/reports/eval-judge-*.csv`

### Files & Structure

```
monitoring/
├── MANUAL_EVALUATION.md          # Q1 documentation
├── evals/
│   ├── generate_data.py          # Q3: Generate ground truth dataset
│   ├── eval_agent_run.py         # Q3: Run agent on questions
│   ├── eval_agent_judge.py       # Q3: Judge evaluation
│   ├── evals_common.py           # Shared utilities
│   ├── run_orchestrator.py       # Run complete pipeline
│   ├── reports/                  # Output results
│   │   ├── eval-run-*.csv        # Agent responses
│   │   └── eval-judge-*.csv      # Judge scores
│   └── ground_truth_emails.csv   # Ground truth dataset
```

### How to Run

#### Option 1: Run Full Pipeline (Recommended)

```bash
cd /workspaces/ai-bootcamp/email-agent/code

# Run complete evaluation pipeline
uv run python -m monitoring.evals.run_orchestrator.py

# Or with options:
uv run python -m monitoring.evals.run_orchestrator.py --sample 10
```

#### Option 2: Step-by-Step

**Step 1: Generate Ground Truth Dataset**
```bash
uv run python -m monitoring.evals.generate_data
```

Creates `monitoring/evals/ground_truth_emails.csv` with:
- Manual questions from Q1
- LLM-generated variations
- Categories and difficulty levels

**Step 2: Run Agent Evaluation**
```bash
uv run python -m monitoring.evals.eval_agent_run
```

Runs agent on all ground truth questions and saves results to:
`monitoring/evals/reports/eval-run-YYYY-MM-DD-HH-MM-SS.csv`

**Step 3: Run Judge Evaluation**
```bash
uv run python -m monitoring.evals.eval_agent_judge

# Or on a sample:
uv run python -m monitoring.evals.eval_agent_judge --sample 10
```

Creates judge scores in:
`monitoring/evals/reports/eval-judge-YYYY-MM-DD-HH-MM-SS.csv`

### Understanding the Results

#### Ground Truth CSV Columns
- `question`: User query
- `expected_approach`: How agent should respond
- `difficulty`: beginner/intermediate/advanced
- `category`: Type of query (search, threading, etc.)
- `source`: manual_q1 or llm_generated

#### Agent Run Results CSV Columns
- `question`: Original query
- `answer`: Agent response (truncated)
- `difficulty`: Question difficulty
- `category`: Query category
- `expected_approach`: Expected behavior
- `source`: Where question came from

#### Judge Evaluation CSV Columns
- `question`: The query evaluated
- `answer`: Agent response (truncated)
- `relevance_score`: 0-10 (is answer relevant?)
- `completeness_score`: 0-10 (complete answer?)
- `accuracy_score`: 0-10 (accurate?)
- `tool_usage_score`: 0-10 (right tools?)
- `overall_score`: 0-100 (average of above)
- `reasoning`: Explanation of scores
- `suggestions`: Improvement suggestions

### Analysis & Insights

#### Sample Analysis Code

```python
import pandas as pd

# Load judge evaluation
df = pd.read_csv("monitoring/evals/reports/eval-judge-*.csv")

# Overall statistics
print(f"Average score: {df['overall_score'].mean():.1f}/100")
print(f"Median score: {df['overall_score'].median():.1f}/100")
print(f"Std deviation: {df['overall_score'].std():.1f}")

# Score distribution
print("\nScore distribution:")
print(df['overall_score'].value_counts(bins=5).sort_index())

# Worst performing questions
worst = df.nsmallest(5, 'overall_score')[['question', 'overall_score', 'reasoning']]
print("\nWorst 5 performing:")
print(worst)

# By category
print("\nAverage by category:")
print(df.groupby('category')['overall_score'].agg(['mean', 'count']))
```

### Expected Metrics

- **Target Average Score**: > 70/100
- **Minimum Acceptable**: > 50/100
- **Success Rate**: >= 80% of questions answered relevantly

## Integration with Week3 Structure

This evaluation system mirrors the week3 code patterns:

| Week3 | Email Agent | Purpose |
|-------|-------------|---------|
| `evals/generate_data.py` | `monitoring/evals/generate_data.py` | Create datasets |
| `evals/eval_agent_run.py` | `monitoring/evals/eval_agent_run.py` | Run agent |
| `evals/eval_agent_judge.py` | `monitoring/evals/eval_agent_judge.py` | Judge evaluation |
| `evals/evals_common.py` | `monitoring/evals/evals_common.py` | Shared utilities |

## Key Improvements to Implement

Based on the three-question framework, you can identify:

1. **From Q1**: Which queries the agent struggles with
2. **From Q2**: Which test categories fail most often
3. **From Q3**: Which question types have lowest scores

Use this data to prioritize improvements:

```
If avg score < 60:  -> Major refactoring needed
If avg score 60-75: -> Refinement of prompts/tools
If avg score 75-85: -> Edge case handling
If avg score > 85:  -> Polish and optimization
```

## Next Steps

1. ✅ **Set up**: All files and structure created
2. ⏳ **Manual test** (Q1): Run agent with 10+ questions
3. ⏳ **Validate tests** (Q2): Run pytest suites
4. ⏳ **Run evals** (Q3): Generate ground truth, run agent, get judge scores

## Troubleshooting

### Import Errors
```bash
cd /workspaces/ai-bootcamp/email-agent/code
uv sync  # Ensure dependencies installed
```

### Agent Not Running
```bash
# Check main.py has agent initialized
python -c "import main; print(main.agent)"

# Check Elasticsearch is running
docker ps | grep elasticsearch
```

### Judge Evaluation Fails
```bash
# Check OpenAI API key
echo $OPENAI_API_KEY

# Check model is available (default: gpt-4o-mini)
```

## References

- Week3 Code: `/workspaces/ai-bootcamp/week3/code/evals/`
- Main Agent: `/workspaces/ai-bootcamp/email-agent/code/email_agent/agent.py`
- Test Suite: `/workspaces/ai-bootcamp/email-agent/code/tests/`
