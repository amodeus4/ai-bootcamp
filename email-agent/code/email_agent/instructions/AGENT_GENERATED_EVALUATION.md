# Agent-Generated Questions Evaluation Guide

This guide explains how to use the Week 3 approach for generating test questions with your email agent.

## Overview

Instead of manually writing test questions, the system uses an LLM to **generate realistic questions from your documentation**. This approach:

- ✅ Creates questions that reflect real user behavior
- ✅ Covers all documented features and capabilities
- ✅ Maintains consistent distribution (beginner/intermediate/advanced)
- ✅ Evaluates both conceptual understanding and tool usage
- ✅ Provides automatic scoring with 8-point rubric

## Quick Start

### 1. Generate Questions

```bash
python -m email_agent.generate_evaluation_data README.md --output evaluation_dataset.csv
```

This will:
- Read your documentation
- Use GPT-4o-mini to generate ~10-15 realistic test questions
- Save results to `evaluation_dataset.csv`
- Show question distribution (difficulty and intent)

### 2. Run Evaluation

Open and run the notebook:
```bash
jupyter notebook generate_evaluation.ipynb
```

The notebook will:
1. Load generated questions from CSV
2. Initialize your email agent
3. Run agent on each question
4. Score responses automatically
5. Generate detailed report

### 3. Review Results

Results are saved to `evaluations/`:
- `results_*.pkl` - Raw evaluation data
- `report_*.txt` - Formatted report
- `results_*.csv` - DataFrame for analysis

## Question Generation Process

### How Questions Are Generated

1. **Read Documentation**: The system loads your README.md
2. **Estimate Questions**: Based on content length (target: ~800 chars per question)
3. **LLM Generation**: Uses OpenAI with structured output to generate questions
4. **Structured Output**: Each question includes:
   - Question text (realistic user query)
   - Summary answer (expected response)
   - Difficulty level (beginner/intermediate/advanced)
   - Intent (text for concepts, code for tool usage)
   - Relevant docs (which features it tests)

### Distribution Rules

The LLM follows these guidelines:
- **60%** beginner-level questions
- **30%** intermediate-level questions
- **10%** advanced-level questions
- **70%** code intent (tool usage and implementation)
- **30%** text intent (conceptual understanding)

### Example Questions Generated

```
Q1: "Show me unread emails" 
    - Difficulty: beginner
    - Intent: code (uses gmail_fetch tool)

Q2: "Find emails about invoices over $5000"
    - Difficulty: hard
    - Intent: code (complex search with filters)

Q3: "What's the attachment format email agent supports?"
    - Difficulty: intermediate
    - Intent: text (conceptual question)
```

## Evaluation Scoring

Each response is evaluated on 8 criteria:

1. **Answer Relevance** (0-10): Does response address the question?
2. **Answer Completeness** (0-10): Does it fully answer the query?
3. **Answer Accuracy** (0-10): Are results factually correct?
4. **Tool Usage Correct** (0-10): Were appropriate tools used?
5. **Tool Usage Efficient** (0-10): Were tools used optimally?
6. **Attachment Handling** (0-10): (if applicable) Proper attachment management?
7. **Threading Context** (0-10): (if applicable) Email thread awareness?
8. **Clarity** (0-10): Is response well-formatted and clear?

### Score Calculation

- **Per-Check Score**: 0-10 points
- **Overall Score**: Percentage of passed checks (pass threshold = 6/10)
- **Pass Rate**: % of checks that scored ≥ 6/10

## Example Report Output

```
================================================================================
📊 EVALUATION REPORT
================================================================================

📈 OVERALL RESULTS:
  Questions evaluated: 12
  Average score: 72.5%
  Passed (≥60%): 10/12

✅ CHECK BREAKDOWN:
  answer_relevant       : 12/12 (100.0%) avg score   8.5/10
  answer_complete       :  9/12 ( 75.0%) avg score   6.8/10
  tool_usage_correct    : 12/12 (100.0%) avg score   9.2/10
  ...

📝 QUESTION BREAKDOWN:
  Q1 [100%]: Show me unread emails
    ✅ answer_relevant     : 10/10 - Strong keyword matching
    ✅ tool_usage_correct  :  9/10 - Gmail tool correctly identified
    ...
```

## Configuration

### Customize Question Generation

Edit the command:

```bash
python -m email_agent.generate_evaluation_data README.md \
    --model gpt-4o-mini \
    --max-workers 4 \
    --output my_questions.csv
```

Options:
- `--model`: OpenAI model (default: gpt-4o-mini)
- `--max-workers`: Parallel workers (default: 6)
- `--output`: CSV output filename

### Add More Documentation

Generate from multiple files:

```bash
python -m email_agent.generate_evaluation_data \
    README.md \
    ATTACHMENT_HANDLING.md \
    --output evaluation_dataset.csv
```

## Troubleshooting

### No Questions Generated

- Check documentation file exists and has content > 500 chars
- Verify OpenAI API key in `.env`
- Check internet connectivity

### Low Evaluation Scores

Possible causes:
- Agent needs better system prompt
- Tools need better descriptions
- Email data missing from Elasticsearch
- Gmail API authentication issues

**Solutions:**
1. Review low-scoring checks in report
2. Update agent system prompt in `agent.py`
3. Re-run evaluation to verify improvements

### Memory Issues During Generation

If using many workers:
```bash
python -m email_agent.generate_evaluation_data README.md --max-workers 2
```

## Next Steps

1. **Run Evaluation**: Execute `generate_evaluation.ipynb`
2. **Review Report**: Check `evaluations/report_*.txt`
3. **Identify Gaps**: Note which checks have low scores
4. **Improve Agent**: Update prompts or tools based on results
5. **Re-evaluate**: Run evaluation again to verify improvements

## File Locations

```
email-agent/code/
├── generate_evaluation.ipynb          # Main evaluation notebook
├── evaluation_dataset.csv              # Generated questions
├── email_agent/
│   ├── generate_evaluation_data.py     # Question generation script
│   ├── manual_evaluator.py             # Evaluation engine
│   └── evaluation_schemas.py           # Data models
└── evaluations/
    ├── results_*.pkl                   # Raw results
    ├── report_*.txt                    # Formatted report
    └── results_*.csv                   # DataFrame export
```

## Comparing with Week 3

Your implementation follows the Week 3 approach:

| Component | Week 3 | Your Project |
|-----------|--------|--------------|
| Question Source | Evidently docs | Agent README |
| Generation | LLM from docs | LLM from docs |
| Tool | toyaikit agents | Email agent |
| Evaluation | Judge model | 8-check rubric |
| Results | CSV + Judge eval | CSV + Auto-scoring |

The key difference: Your evaluation uses automatic scoring instead of a separate judge model, making it faster and more reproducible.
