# Email Agent

An intelligent email management agent powered by OpenAI's GPT-4, Gmail API, and Elasticsearch.

## Features

- 📧 Fetch emails from Gmail
- 🔍 Search emails in Elasticsearch
- 🤖 Natural language chat interface
- ✅ Organize and categorize emails
- 💾 Persistent email storage and indexing

## Prerequisites

- Python 3.12+
- `uv` package manager
- Gmail API credentials
- Elasticsearch instance (local or remote)

## Setup

### 1. Clone and Navigate

```bash
cd email-agent/code
```

### 2. Install Dependencies

```bash
make install
# or manually: uv sync
```

### 3. Configure Environment

```bash
make setup
# This creates .env from .env.example
```

Edit `.env` with your configuration:
- `CREDENTIALS_FILE`: Path to your Gmail API credentials.json
- `ES_HOST`: Elasticsearch host (default: localhost)
- `ES_PORT`: Elasticsearch port (default: 9200)
- `ES_INDEX_NAME`: Index name for emails (default: emails)
- `OPENAI_API_KEY`: Your OpenAI API key

### 4. Set Up Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the Gmail API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download credentials as `credentials.json` and place in `email-agent/code/`

### 5. Start Elasticsearch

```bash
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e discovery.type=single-node \
  -e xpack.security.enabled=false \
  docker.elastic.co/elasticsearch/elasticsearch:9.1.1
```

Or if you already have it running:
```bash
docker start elasticsearch
```

### 6. Run the Agent

#### Option A: Command Line Interface (CLI)

```bash
make run
# or manually: uv run main.py
```

On first run, the agent will:
1. Authenticate with Gmail
2. Fetch and index your emails
3. Start an interactive chat session

#### Option B: Streamlit Web Interface (Recommended)

```bash
make streamlit
# or manually: uv run streamlit run streamlit_app.py --server.port 8501
```

This will start the web interface at `http://localhost:8501` with:
- 💬 Chat interface with your email agent
- 📊 Real-time monitoring and evaluation
- 🔍 Tool call visualization
- 📈 Performance metrics and response quality checks

## How It Works

### Architecture

The Email Agent is a multi-component intelligent system that combines:

1. **Gmail API Integration**: Authenticates and fetches emails from your Gmail account
2. **Elasticsearch Storage**: Indexes and stores emails for fast semantic search
3. **OpenAI GPT-4**: Powers natural language understanding and response generation
4. **Tool-based Agent**: Uses multiple specialized tools to handle different email operations
5. **Monitoring System**: Tracks conversations, evaluates responses, and provides analytics

### Agent Tools

The agent has access to the following tools:

- **GmailFetchTool**: Fetches emails directly from Gmail API
- **ElasticsearchSearchTool**: Searches indexed emails using semantic and keyword search
- **ElasticsearchWriteTool**: Indexes new emails into Elasticsearch
- **ConversationHistoryTool**: Retrieves past conversation context
- **SearchAttachmentsTool**: Finds emails with specific attachments
- **CategorizeEmailsTool**: Organizes emails into categories (work, personal, promotions, etc.)
- **PriorityInboxTool**: Identifies and prioritizes important emails

### Workflow

1. **First Run**:
   - Authenticates with Gmail (OAuth2 flow)
   - Fetches all emails from your inbox
   - Indexes emails into Elasticsearch with metadata (sender, subject, date, body, attachments)

2. **Chat Interaction**:
   - You ask a question in natural language
   - GPT-4 analyzes your query and decides which tools to use
   - Tools are executed (fetch, search, categorize, etc.)
   - Agent synthesizes results and responds in natural language

3. **Monitoring** (Streamlit only):
   - Each conversation is logged with timestamps
   - Tool calls are tracked
   - Automatic evaluations check response quality
   - Performance metrics (response time, success rate) are recorded

### Example Queries

```
You: Show my unread emails
Agent: [uses GmailFetchTool to fetch unread emails]

You: Find emails from john@example.com about the proposal
Agent: [uses ElasticsearchSearchTool with filters]

You: What are my most important emails today?
Agent: [uses PriorityInboxTool to rank by importance]

You: Show me emails with PDF attachments
Agent: [uses SearchAttachmentsTool to filter by attachment type]

You: Organize my inbox by category
Agent: [uses CategorizeEmailsTool to classify emails]
```

## Monitoring Dashboard

The project includes a separate monitoring dashboard to analyze agent performance:

```bash
make monitoring
# or manually: uv run streamlit run monitoring_app.py --server.port 8502
```

Access at `http://localhost:8502` to view:

- 📊 **Conversation Analytics**: Track all user interactions over time
- ✅ **Quality Metrics**: Response quality checks and success rates
- 🔧 **Tool Usage**: See which tools are used most frequently
- ⏱️ **Performance**: Response times and latency analysis
- 📝 **Manual Evaluation**: Review and provide feedback on agent responses

## Project Structure

```
email-agent/code/
├── email_agent/           # Main package
│   ├── __init__.py
│   ├── agent.py           # EmailAgent class
│   ├── schemas.py         # Data models
│   ├── gmail_client.py    # Gmail API integration
│   ├── elasticsearch_store.py  # ES operations
│   └── tools/
│       └── __init__.py    # Tool definitions
├── tests/                 # Unit tests
├── main.py                # Entry point
├── pyproject.toml         # Dependencies
├── .env.example           # Environment template
├── Makefile               # Commands
└── README.md              # This file
```

## Development

### Run Tests

```bash
uv run pytest -s
```

### Clean Cache

```bash
make clean
```

## Troubleshooting

### Elasticsearch Connection Error

Make sure Elasticsearch is running:
```bash
docker ps | grep elasticsearch
```

If not running:
```bash
docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 -e discovery.type=single-node -e xpack.security.enabled=false docker.elastic.co/elasticsearch/elasticsearch:9.1.1
```

### Gmail Authentication Error

- Delete `token.pickle` to re-authenticate
- Ensure `credentials.json` is in the correct location
- Check that Gmail API is enabled in Google Cloud Console

### No Emails Indexed

- Check Gmail API credentials
- Verify network connectivity
- Check Elasticsearch is accessible

## Requirements

See `pyproject.toml` for full dependencies:
- google-auth-oauthlib
- google-api-python-client
- elasticsearch
- openai
- pydantic
- python-dotenv

## License

MIT
