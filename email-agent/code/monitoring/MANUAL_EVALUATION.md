# Question 1: Manual Evaluation

## Overview
This document contains manual evaluation of the email agent by interacting with it through various questions and observing the results.

## Evaluation Process

### Setup
- Agent: Email management agent powered by OpenAI + Elasticsearch
- Tools available:
  - `gmail_fetch`: Retrieve unread emails
  - `elasticsearch_search`: Search through email history
  - `conversation_history`: Get all emails from a specific sender
  - `search_attachments`: Search within email attachments
  - `elasticsearch_write`: Update email information

### Test Questions (10+)

Below are the manual test questions used to evaluate the agent:

#### 1. **Basic Unread Email Query**
- **Question**: "Show me my unread emails"
- **Expected Tool**: `gmail_fetch` with `query="is:unread"`
- **Expected Behavior**: Fetch and display unread emails
- **Result**: ✅ shows max 10
- **Notes**: Basic functionality test

#### 2. **Date-Range Search**
- **Question**: "What emails did I receive in the last week?"
- **Expected Tool**: `elasticsearch_search` with date range
- **Expected Behavior**: Search emails from last 7 days
- **Result**: ❌ only showing Nov 24
- **Notes**: Tests temporal filtering

#### 3. **Sender-Based Query**
- **Question**: "What emails are from my boss?"
- **Expected Tool**: `elasticsearch_search` with sender filter
- **Expected Behavior**: Find and list emails from boss
- **Result**: ✅ answers those that are in elasticsearch
- **Notes**: Tests sender-based filtering

#### 4. **Conversation Thread**
- **Question**: "Show me the full conversation for MYS USA - Inv. 2025-002LH - USD 5,130.78"
- **Expected Tool**: `conversation_history` with sender email
- **Expected Behavior**: Retrieve all emails from Alice
- **Result**: ❌ only showing me ones from my boss
- **Notes**: Tests conversation threading capability

#### 5. **Attachment Search**
- **Question**: "Find emails with PDF attachments from last month"
- **Expected Tool**: `search_attachments` + `elasticsearch_search` (date range)
- **Expected Behavior**: Search for emails with specific document types
- **Result**: ❌ not finding anything
- **Notes**: Tests attachment handling

#### 6. **Keyword Search**
- **Question**: "Show me all emails mentioning invoices"
- **Expected Tool**: `elasticsearch_search` with keyword
- **Expected Behavior**: Find emails containing specific text
- **Result**: ✅ found them (they are recent)
- **Notes**: Tests full-text search

#### 7. **Attachment Content Search**
- **Question**: "Find any invoices over $5000 in my emails"
- **Expected Tool**: `search_attachments` to search within documents
- **Expected Behavior**: Locate specific content in attachments
- **Result**:  ❌ can't parse PDFs
- **Notes**: Tests advanced attachment search

#### 8. **Category-Based Query**
- **Question**: "What emails are marked as important?"
- **Expected Tool**: `elasticsearch_search` with category filter
- **Expected Behavior**: Filter emails by category/label
- **Result**: ❌ couldn't find them
- **Notes**: Tests label/category filtering

#### 9. **Follow-up Question**
- **Question**: "From the previous results, which one has attachments?"
- **Expected Tool**: Uses conversation history + analysis
- **Expected Behavior**: Reference previous context and filter
- **Result**: ✅ [found the email]
- **Notes**: Tests multi-turn conversation capability

#### 10. **Recipient-Based Query**
- **Question**: "Who did I email about sending an invoice over for VIV?"
- **Expected Tool**: `elasticsearch_search` with recipient filters
- **Expected Behavior**: Find emails sent to specific recipients
- **Result**: ✅ found the email
- **Notes**: Tests recipient filtering

#### 11. **Negative Query (Edge Case)**
- **Question**: "Show me emails that don't have attachments"
- **Expected Tool**: `elasticsearch_search` with exclusion
- **Expected Behavior**: Handle negative/exclusion queries
- **Result**: ❌ couldn't find them
- **Notes**: Tests edge case handling

## Observations & Analysis

### What Makes Sense
- ✅ Tool selection logic appears sound
- ✅ System prompt covers main use cases
- ✅ Error handling structure is present

### What Needs Improvement
1. **Attachment Search**: May need refinement in matching document content
2. **Complex Queries**: Multi-criteria queries might need better tool chaining
3. **Context Preservation**: Conversation history handling could be optimized
4. **Edge Cases**: Negative queries and exclusions need better handling

### Pattern Analysis

#### Tool Usage Patterns
- **Most used tools**: `elasticsearch_search`, `conversation_history`
- **Least used tools**: `elasticsearch_write`
- **Tool selection accuracy**: [To be determined]

#### Response Quality
- **Relevance**: [To be evaluated by judge]
- **Completeness**: [To be evaluated by judge]
- **Accuracy**: [To be evaluated by judge]

### Issue Log

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| 1 | [To be documented] | [Low/Medium/High] | [New/In Progress/Resolved] |
| 2 | [To be documented] | [Low/Medium/High] | [New/In Progress/Resolved] |
| 3 | [To be documented] | [Low/Medium/High] | [New/In Progress/Resolved] |

## Recommendations for Improvement

### Immediate Actions
1. Refine tool selection logic for complex queries
2. Improve error messages for unsupported queries
3. Add better validation for email addresses and search terms

### Medium-term Improvements
1. Add caching for frequently accessed conversations
2. Implement response ranking/filtering
3. Enhance attachment metadata extraction

### Long-term Enhancements
1. Add machine learning for tool selection
2. Implement user preference learning
3. Add multi-language support
4. Implement advanced RAG for document understanding

## Summary

- **Total Questions Asked**: 12
- **Test Coverage**: Comprehensive (basic, intermediate, advanced)
- **Overall Assessment**: [To be filled after testing]
- **Ready for Evaluation**: ✅ Yes
- **Ground Truth Dataset**: ✅ Created in `monitoring/evals/ground_truth_emails.csv`
