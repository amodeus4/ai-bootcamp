#!/bin/bash
# Quick start script for agent-generated evaluation

set -e

echo "🚀 Email Agent - Agent-Generated Evaluation Setup"
echo "=================================================="
echo ""

# Step 1: Generate questions
echo "📝 Step 1: Generating test questions from documentation..."
echo "   Running: python -m email_agent.generate_evaluation_data README.md"
echo ""

python -m email_agent.generate_evaluation_data README.md

echo ""
echo "✅ Questions generated! Saved to: evaluation_dataset.csv"
echo ""

# Step 2: Show next steps
echo "📋 Step 2: Next steps"
echo "   1. Open Jupyter notebook:"
echo "      jupyter notebook generate_evaluation.ipynb"
echo ""
echo "   2. Or run evaluation directly:"
echo "      python -c \""
echo "from email_agent import ManualEvaluator, authenticate_gmail, ElasticsearchEmailStore, EmailAgent"
echo "from dotenv import load_dotenv"
echo "import os"
echo "load_dotenv()"
echo ""
echo "gmail = authenticate_gmail()"
echo "es = ElasticsearchEmailStore()"
echo "agent = EmailAgent(gmail_service=gmail, es_store=es)"
echo ""
echo "evaluator = ManualEvaluator()"
echo "dataset = evaluator.load_dataset_from_csv('evaluation_dataset.csv')"
echo "results = evaluator.run_evaluation(agent, dataset)"
echo "evaluator.print_report()"
echo "evaluator.save_report('evaluation_report.txt')"
echo "      \""
echo ""
echo "📚 For more details, see:"
echo "   - AGENT_GENERATED_EVALUATION.md (comprehensive guide)"
echo "   - IMPLEMENTATION_SUMMARY.md (quick overview)"
echo ""
